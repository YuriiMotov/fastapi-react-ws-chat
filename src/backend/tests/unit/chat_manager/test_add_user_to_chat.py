import uuid
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatNotification, ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.event import ChatListUpdate, UserAddedToChatNotification
from backend.services.chat_manager.chat_manager import (
    USER_JOINED_CHAT_NOTIFICATION,
    ChatManager,
)
from backend.services.chat_manager.chat_manager_exc import (
    BadRequest,
    EventBrokerError,
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.event_broker.event_broker_exc import EventBrokerException
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker


async def test_add_user_to_chat_success(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Successful execution of add_user_to_chat() creates a user-chat
    association record in the database.
    """
    # Create User and Chat
    chat_owner_id = event_broker_user_id_list[0]
    user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Check that UserChatLink record was added to the DB
    async_session.expire_all()
    user_chat_link = await async_session.scalar(
        select(UserChatLink)
        .where(UserChatLink.chat_id == chat_id)
        .where(UserChatLink.user_id == user_id)
    )
    assert user_chat_link is not None


async def test_add_user_to_chat_notification_added_to_db(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Successful execution of add_user_to_chat() creates a notification
    record in the database.
    """
    # Create User and Chat
    chat_owner_id = event_broker_user_id_list[0]
    user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Check that ChatNotification record was added to the DB
    async_session.expire_all()
    res = await async_session.scalars(
        select(ChatNotification).where(ChatNotification.chat_id == chat_id)
    )
    notifications = res.all()
    assert len(notifications) == 1
    assert notifications[0].text == USER_JOINED_CHAT_NOTIFICATION
    assert notifications[0].params == str(user_id)


async def test_add_user_to_chat_notification_posted_to_mb(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Successful execution of add_user_to_chat() posts a notification
    record to the Event broker.
    """
    # Create User and Chat, subscribe user for updates
    chat_owner_id = event_broker_user_id_list[0]
    user_id = event_broker_user_id_list[1]
    other_user_id = event_broker_user_id_list[2]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()
    await chat_manager.event_broker.subscribe(
        channel=channel_code("chat", chat_id), user_id=other_user_id
    )

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Check that notification event was posted
    events = await chat_manager.event_broker.get_events(user_id=other_user_id)
    assert len(events) == 1
    event_json = events[0].model_dump_json()
    assert USER_JOINED_CHAT_NOTIFICATION in event_json
    assert str(user_id) in event_json


async def test_add_user_to_chat__user_gets_subscribet_for_chat_updates(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    After successful execution of add_user_to_chat(), user is subscribed for chat
    updates.
    """
    # Create User and Chat, subscribe user for updates
    chat_owner_id = event_broker_user_id_list[0]
    user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()

    # Subscribe user to events
    await chat_manager.subscribe_for_updates(current_user_id=user_id)

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Check that added user was subscribed for updates
    with patch.object(InMemoryEventBroker, "subscribe") as patched_method:
        events = await chat_manager.get_events(current_user_id=user_id)
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserAddedToChatNotification)
        if isinstance(event, UserAddedToChatNotification):
            assert event.chat_id == chat_id
        patched_method.assert_awaited_once_with(
            channel=channel_code("chat", chat_id), user_id=user_id
        )


async def test_add_user_to_chat__chat_list_update_event_sent(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    After successful execution of add_user_to_chat(), ChatListUpdate event with
    appropriate chat data is sent to user.
    """
    # Create User and Chat, ChatUserMessage, subscribe user for updates
    chat_owner_id = event_broker_user_id_list[0]
    user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    message = ChatUserMessage(chat_id=chat_id, text="my message", sender_id=user_id)
    async_session.add_all((user, chat, message))
    await async_session.commit()

    # Subscribe user to events
    await chat_manager.subscribe_for_updates(current_user_id=user_id)

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Receive and acknowledge UserAddedToChatNotification
    events = await chat_manager.get_events(current_user_id=user_id)
    assert len(events) == 1
    assert isinstance(events[0], UserAddedToChatNotification)
    await chat_manager.acknowledge_events(current_user_id=user_id)

    # Check that added user receives ChatListUpdate event
    events = await chat_manager.get_events(current_user_id=user_id)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, ChatListUpdate)
    if isinstance(event, ChatListUpdate):
        assert event.chat_data.id == chat_id
        assert event.chat_data.members_count == 1
        assert event.chat_data.last_message_text == message.text


async def test_add_user_to_chat_wrong_chat_id(
    async_session: AsyncSession, chat_manager: ChatManager
):
    """
    Attempt to call add_user_to_chat() with wrong chat_id (chat doesn't exist) raises
    BadRequest error
    """
    # Create User
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    user = User(id=user_id, name="")
    async_session.add(user)
    await async_session.commit()

    # Call chat_manager.add_user_to_chat()
    with pytest.raises(BadRequest):
        await chat_manager.add_user_to_chat(
            current_user_id=user_id, user_id=user_id, chat_id=chat_id
        )

    # Check that UserChatLink record was not added to the DB
    async_session.expire_all()
    user_chat_link = await async_session.scalar(
        select(UserChatLink)
        .where(UserChatLink.chat_id == chat_id)
        .where(UserChatLink.user_id == user_id)
    )
    assert user_chat_link is None


async def test_add_user_to_chat_user_unauthorized(
    async_session: AsyncSession, chat_manager: ChatManager
):
    """
    Attempt to call add_user_to_chat() without authorization to add users to this
    chat (current_user is not a chat owner) raises UnauthorizedAction
    """
    # Create User
    chat_owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()

    # Call chat_manager.add_user_to_chat()
    with pytest.raises(UnauthorizedAction):
        await chat_manager.add_user_to_chat(
            current_user_id=user_id,  # user_id is not an owner of this chat
            user_id=user_id,
            chat_id=chat_id,
        )

    # Check that UserChatLink record was not added to the DB
    async_session.expire_all()
    user_chat_link = await async_session.scalar(
        select(UserChatLink)
        .where(UserChatLink.chat_id == chat_id)
        .where(UserChatLink.user_id == user_id)
    )
    assert user_chat_link is None


@pytest.mark.parametrize("failure_method", ("add_user_to_chat", "add_notification"))
async def test_add_user_to_chat_repo_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    add_user_to_chat() raises RepositoryError in case of repository failure
    """
    # Create User and Chat
    chat_owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call add_user_to_chat() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.add_user_to_chat(
                current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
            )


@pytest.mark.parametrize("failure_method", ("post_event",))
async def test_add_user_to_chat_event_broker_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    failure_method: str,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    add_user_to_chat() raises EventBrokerError if EventBroker raises error
    """
    # Create User and Chat
    chat_owner_id = event_broker_user_id_list[0]
    user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()

    # Patch InMemoryEventBroker.{failure_method} method so that it always raises
    # EventBrokerException
    with patch.object(
        InMemoryEventBroker,
        failure_method,
        new=Mock(side_effect=EventBrokerException()),
    ):
        # Call add_user_to_chat() and check that it raises EventBrokerError
        with pytest.raises(EventBrokerError):
            await chat_manager.add_user_to_chat(
                current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
            )
