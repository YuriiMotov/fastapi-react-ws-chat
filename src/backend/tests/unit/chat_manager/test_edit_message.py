import uuid
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.event import ChatMessageEdited
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    EventBrokerError,
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_repo.chat_repo_exc import ChatRepoDatabaseError
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.event_broker.event_broker_exc import EventBrokerFail
from backend.services.uow.sqla_uow import SQLAlchemyUnitOfWork


async def test_edit_message__success(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Successful execution of edit_message() updates message text in the DB
    """
    # Create message in the DB
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    message = ChatUserMessage(chat_id=chat_id, text="my message", sender_id=user_id)
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)

    # Call chat_manager.edit_message()
    new_text = "updated text"
    await chat_manager.edit_message(
        current_user_id=user_id, message_id=message.id, text=new_text
    )

    # Check that message in DB was updated
    await async_session.refresh(message)
    assert message.text == new_text


async def test_edit_message__edited_message_event_sent(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    After successful execution of edit_message(), the ChatMessageEdited is sent to
    all chat members.
    """
    # Create chat, users, add users to chat, create message
    user_1_id = event_broker_user_id_list[0]
    user_2_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    user_1 = User(id=user_1_id, name="user 1")
    user_2 = User(id=user_2_id, name="user 2")
    user_chat_link_1 = UserChatLink(user_id=user_1_id, chat_id=chat_id)
    user_chat_link_2 = UserChatLink(user_id=user_2_id, chat_id=chat_id)
    chat = Chat(id=chat_id, title="chat", owner_id=user_1_id)
    message = ChatUserMessage(chat_id=chat_id, text="my message", sender_id=user_1_id)
    async_session.add_all(
        [user_1, user_2, chat, user_chat_link_1, user_chat_link_2, message]
    )
    await async_session.commit()
    await async_session.refresh(message)

    # Subscribe users for updates
    await chat_manager.subscribe_for_updates(current_user_id=user_1_id)
    await chat_manager.subscribe_for_updates(current_user_id=user_2_id)

    # Call chat_manager.edit_message()
    new_text = "updated text"
    await chat_manager.edit_message(
        current_user_id=user_1_id, message_id=message.id, text=new_text
    )

    # Receive user_1 events, check that ChatMessageEdited was received
    user_1_events = await chat_manager.get_events(current_user_id=user_1_id)
    assert len(user_1_events) == 1
    assert isinstance(user_1_events[0], ChatMessageEdited)
    assert user_1_events[0].message.id == message.id
    assert user_1_events[0].message.text == new_text

    # Receive user_2 events, check that ChatMessageEdited was received
    user_2_events = await chat_manager.get_events(current_user_id=user_2_id)
    assert len(user_2_events) == 1
    assert isinstance(user_2_events[0], ChatMessageEdited)
    assert user_2_events[0].message.id == message.id
    assert user_2_events[0].message.text == new_text


async def test_edit_message__unauthorized_access(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Attempt to call edit_message() to edit the message of another user will raise
    UnauthorizedAction
    """
    # Create message in the DB
    user_id = event_broker_user_id_list[0]
    other_user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    message_text = "my message"
    message = ChatUserMessage(
        chat_id=chat_id, text=message_text, sender_id=other_user_id
    )
    async_session.add(message)
    await async_session.commit()
    await async_session.refresh(message)
    new_text = "updated text"

    # Attempt to edit message of another user
    with pytest.raises(UnauthorizedAction):
        await chat_manager.edit_message(
            current_user_id=user_id, message_id=message.id, text=new_text
        )

    # Check that message in DB was not updated
    await async_session.refresh(message)
    assert message.text == message_text


async def test_edit_message__db_update_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    edit_message() raises RepositoryError in case of DB update method failure.
    Message in the DB remains unchanged.
    ChatMessageEdited event is not posted to EventBroker.
    """
    # Create message, user, chat and user-chat link in the DB
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    initial_text = "my message"
    new_text = "updated text"

    message = ChatUserMessage(chat_id=chat_id, text=initial_text, sender_id=user_id)
    user = User(id=user_id, name="user 1")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    chat = Chat(id=chat_id, title="chat", owner_id=user_id)
    async_session.add_all((message, user, user_chat_link, chat))
    await async_session.commit()
    await async_session.refresh(message)

    # Subscribe user for updates
    await chat_manager.subscribe_for_updates(current_user_id=user_id)

    # Brake SQLAlchemyChatRepo.edit_message() method
    with patch.object(
        SQLAlchemyChatRepo,
        "edit_message",
        new=Mock(side_effect=ChatRepoDatabaseError()),
    ):
        # Call chat_manager.edit_message()
        with pytest.raises(RepositoryError):
            await chat_manager.edit_message(
                current_user_id=user_id, message_id=message.id, text=new_text
            )

    # Check that message in DB was not updated
    await async_session.refresh(message)
    assert message.text == initial_text

    # Check that ChatMessageEdited was not posted to the EventBroker
    user_events = await chat_manager.get_events(current_user_id=user_id)
    assert len(user_events) == 0


async def test_edit_message__db_commit_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    edit_message() raises RepositoryError in case of DB commit failure.
    Message in the DB remains unchanged.
    ChatMessageEdited event is not posted to EventBroker.
    """
    # Create message, user, chat and user-chat link in the DB
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    initial_text = "my message"
    new_text = "updated text"

    message = ChatUserMessage(chat_id=chat_id, text=initial_text, sender_id=user_id)
    user = User(id=user_id, name="user 1")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    chat = Chat(id=chat_id, title="chat", owner_id=user_id)
    async_session.add_all((message, user, user_chat_link, chat))
    await async_session.commit()
    await async_session.refresh(message)

    # Subscribe user for updates
    await chat_manager.subscribe_for_updates(current_user_id=user_id)

    # Brake SQLAlchemyUnitOfWork.commit() method
    with patch.object(
        SQLAlchemyUnitOfWork, "commit", new=Mock(side_effect=ChatRepoDatabaseError())
    ):
        # Call chat_manager.edit_message()
        with pytest.raises(RepositoryError):
            await chat_manager.edit_message(
                current_user_id=user_id, message_id=message.id, text=new_text
            )

    # Check that message in DB was not updated
    await async_session.refresh(message)
    assert message.text == initial_text

    # Check that ChatMessageEdited was not posted to the EventBroker - this fails so far
    user_events = await chat_manager.get_events(current_user_id=user_id)
    pytest.xfail("It's needed to use transaction in EventBroker")
    assert len(user_events) == 0


async def test_edit_message__event_broker_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    edit_message() raises EventBrokerError in case of EventBroker failure.
    Message in the DB remains unchanged.
    ChatMessageEdited event is not posted to EventBroker.
    """
    # Create message, user, chat and user-chat link in the DB
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    initial_text = "my message"
    new_text = "updated text"

    message = ChatUserMessage(chat_id=chat_id, text=initial_text, sender_id=user_id)
    user = User(id=user_id, name="user 1")
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    chat = Chat(id=chat_id, title="chat", owner_id=user_id)
    async_session.add_all((message, user, user_chat_link, chat))
    await async_session.commit()
    await async_session.refresh(message)

    # Subscribe user for updates
    await chat_manager.subscribe_for_updates(current_user_id=user_id)

    # Brake chat_manager.event_broker.post_event() method
    with patch.object(
        chat_manager.event_broker, "post_event", new=Mock(side_effect=EventBrokerFail())
    ):
        # Call chat_manager.edit_message()
        with pytest.raises(EventBrokerError):
            await chat_manager.edit_message(
                current_user_id=user_id, message_id=message.id, text=new_text
            )

    # Check that message in DB was not updated
    await async_session.refresh(message)
    assert message.text == initial_text

    # Check that ChatMessageEdited was not posted to the EventBroker
    user_events = await chat_manager.get_events(current_user_id=user_id)
    assert len(user_events) == 0
