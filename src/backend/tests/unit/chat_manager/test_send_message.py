import uuid
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.chat_message import ChatUserMessageCreateSchema
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    EventBrokerError,
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.event_broker.event_broker_exc import EventBrokerException
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker


async def test_send_message_success(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Successful execution of send_message() creates a ChatUserMessage
    record in the DB.
    """
    # Create User, Chat, UserChatLink
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
    user = User(id=user_id, name="")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    async_session.add_all((user, chat, user_chat_link))
    await async_session.commit()

    # Call chat_manager.send_message()
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )
    await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that ChatUserMessage record was added to the DB
    async_session.expire_all()
    res = await async_session.scalars(
        select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
    )
    messages = res.all()
    assert len(messages) == 1
    assert messages[0].text == message.text


async def test_send_message_success_added_to_event_broker_queue(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Successful execution of send_message() adds an event to the Event broker's queue
    """
    # Create User, Chat, UserChatLink
    user_id = event_broker_user_id_list[0]
    other_user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
    user = User(id=user_id, name="")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    async_session.add_all((user, chat, user_chat_link))
    await async_session.commit()

    # Subscribe other_user to channel of the same chat
    await chat_manager.event_broker.subscribe(
        channel=channel_code("chat", chat_id), user_id=other_user_id
    )

    # Call chat_manager.send_message()
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"message {uuid.uuid4()}", sender_id=user_id
    )
    await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that other_user receives event via Event broker
    events = await chat_manager.event_broker.get_events_str(user_id=other_user_id)
    assert len(events) == 1
    assert message.text in events[0]


async def test_send_message_wrong_sender(
    async_session: AsyncSession, chat_manager: ChatManager
):
    """
    Calling send_message() with wrong sender_id raises UnauthorizedAction
    """
    # Create User, Chat, UserChatLink
    user_id = uuid.uuid4()
    wrong_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
    user = User(id=user_id, name="")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    async_session.add_all((user, chat, user_chat_link))
    await async_session.commit()

    # Call chat_manager.send_message() with wrong sender_id and check that exception
    # is raised
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=wrong_user_id
    )
    with pytest.raises(UnauthorizedAction):
        await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that ChatUserMessage wasn't added to the DB
    async_session.expire_all()
    res = await async_session.scalars(
        select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
    )
    messages = res.all()
    assert len(messages) == 0


async def test_send_message_user_not_a_chat_member(
    async_session: AsyncSession, chat_manager: ChatManager
):
    """
    Calling send_message() with sender_id who is not a chat member
    raises UnauthorizedAction
    """
    # Create User, Chat
    user_id = uuid.uuid4()
    wrong_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
    user = User(id=user_id, name="")
    async_session.add_all((user, chat))
    await async_session.commit()

    # Call chat_manager.send_message() with user who is not a chat member and check
    # that exception is raised
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=wrong_user_id
    )
    with pytest.raises(UnauthorizedAction):
        await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that ChatUserMessage wasn't added to the DB
    async_session.expire_all()
    res = await async_session.scalars(
        select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
    )
    messages = res.all()
    assert len(messages) == 0


@pytest.mark.parametrize("failure_method", ("add_message",))
async def test_send_message_repo_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    send_message() raises RepositoryError in case of repository failure
    """
    # Create User and Chat, add User to Chat
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
    user = User(id=user_id, name="")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    async_session.add_all((user, chat, user_chat_link))
    await async_session.commit()
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call join_chat() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.send_message(current_user_id=user_id, message=message)


@pytest.mark.parametrize("failure_method", ("post_event_str",))
async def test_send_message_event_broker_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    send_message() raises EventBrokerError in case of Event broker failure
    """
    # Create User and Chat, add User to Chat
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
    user = User(id=user_id, name="")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    async_session.add_all((user, chat, user_chat_link))
    await async_session.commit()
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )

    # Patch InMemoryEventBroker.{failure_method} method so that it always raises
    # EventBrokerException
    with patch.object(
        InMemoryEventBroker,
        failure_method,
        new=Mock(side_effect=EventBrokerException()),
    ):
        # Call join_chat() and check that it raises EventBrokerError
        with pytest.raises(EventBrokerError):
            await chat_manager.send_message(current_user_id=user_id, message=message)
