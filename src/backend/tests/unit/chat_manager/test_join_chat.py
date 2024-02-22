import uuid
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.chat import Chat
from backend.models.chat_message import ChatNotification
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.chat_message import ChatNotificationSchema
from backend.services.chat_manager.chat_manager import (
    USER_JOINED_CHAT_NOTIFICATION,
    ChatManager,
)
from backend.services.chat_manager.chat_manager_exc import (
    BadRequest,
    MessageBrokerError,
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.message_broker.in_memory_message_broker import (
    InMemoryMessageBroker,
)
from backend.services.message_broker.message_broker_exc import MessageBrokerException


async def test_add_user_to_chat_success(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of add_user_to_chat() creates a user-chat
    association record in the database.
    """
    # Create User and Chat
    chat_owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Check that UserChatLink record was added to the DB
    async with async_session_maker() as session:
        user_chat_link = await session.scalar(
            select(UserChatLink)
            .where(UserChatLink.chat_id == chat_id)
            .where(UserChatLink.user_id == user_id)
        )
        assert user_chat_link is not None


async def test_add_user_to_chat_notification_added_to_db(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of add_user_to_chat() creates a notification
    record in the database.
    """
    # Create User and Chat
    chat_owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Check that ChatNotification record was added to the DB
    async with async_session_maker() as session:
        res = await session.scalars(
            select(ChatNotification).where(ChatNotification.chat_id == chat_id)
        )
        notifications = res.all()
    assert len(notifications) == 1
    assert notifications[0].text == USER_JOINED_CHAT_NOTIFICATION
    assert notifications[0].params == str(user_id)


async def test_add_user_to_chat_notification_posted_to_mb(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of add_user_to_chat() posts a notification
    record to the message broker.
    """
    # Create User and Chat, subscribe user for updates
    chat_owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()
    await chat_manager.message_broker.subscribe(
        channel=channel_code("chat", chat_id), user_id=other_user_id
    )

    # Call chat_manager.add_user_to_chat()
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
    )

    # Check that notification message was posted
    chat_messages = await chat_manager.message_broker.get_messages(
        user_id=other_user_id
    )
    assert len(chat_messages) == 1
    notification = ChatNotificationSchema.model_validate_json(chat_messages[0])
    assert notification.text == USER_JOINED_CHAT_NOTIFICATION
    assert notification.params == str(user_id)


async def test_add_user_to_chat_wrong_chat_id(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Attempt to call add_user_to_chat() with wrong chat_id (chat doesn't exist) raises
    BadRequest error
    """
    # Create User
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        user = User(id=user_id, name="")
        session.add(user)
        await session.commit()

    # Call chat_manager.add_user_to_chat()
    with pytest.raises(BadRequest):
        await chat_manager.add_user_to_chat(
            current_user_id=user_id, user_id=user_id, chat_id=chat_id
        )

    # Check that UserChatLink record was not added to the DB
    async with async_session_maker() as session:
        user_chat_link = await session.scalar(
            select(UserChatLink)
            .where(UserChatLink.chat_id == chat_id)
            .where(UserChatLink.user_id == user_id)
        )
        assert user_chat_link is None


async def test_add_user_to_chat_user_unauthorized(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Attempt to call add_user_to_chat() without authorization to add users to this
    chat (current_user is not a chat owner) raises UnauthorizedAction
    """
    # Create User
    chat_owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    # Call chat_manager.add_user_to_chat()
    with pytest.raises(UnauthorizedAction):
        await chat_manager.add_user_to_chat(
            current_user_id=user_id,  # user_id is not an owner of this chat
            user_id=user_id,
            chat_id=chat_id,
        )

    # Check that UserChatLink record was not added to the DB
    async with async_session_maker() as session:
        user_chat_link = await session.scalar(
            select(UserChatLink)
            .where(UserChatLink.chat_id == chat_id)
            .where(UserChatLink.user_id == user_id)
        )
        assert user_chat_link is None


@pytest.mark.parametrize("failure_method", ("add_user_to_chat", "add_notification"))
async def test_add_user_to_chat_repo_failure(
    async_session_maker: async_sessionmaker,
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
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

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


@pytest.mark.parametrize("failure_method", ("post_message", "subscribe"))
async def test_add_user_to_chat_message_broker_failure(
    async_session_maker: async_sessionmaker,
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    add_user_to_chat() raises MessageBrokerError if MessageBroker raises error
    """
    # Create User and Chat
    chat_owner_id = uuid.uuid4()
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=chat_owner_id)
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    # Patch InMemoryMessageBroker.{failure_method} method so that it always raises
    # MessageBrokerException
    with patch.object(
        InMemoryMessageBroker,
        failure_method,
        new=Mock(side_effect=MessageBrokerException()),
    ):
        # Call add_user_to_chat() and check that it raises MessageBrokerError
        with pytest.raises(MessageBrokerError):
            await chat_manager.add_user_to_chat(
                current_user_id=chat_owner_id, user_id=user_id, chat_id=chat_id
            )
