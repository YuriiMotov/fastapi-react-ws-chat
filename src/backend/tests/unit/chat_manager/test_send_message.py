import uuid
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.chat_message import (
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
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


async def test_send_message_success(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of send_message() creates a ChatUserMessage
    record in the DB.
    """
    # Create User, Chat, UserChatLink
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
        session.add_all((user, chat, user_chat_link))
        await session.commit()

    # Call chat_manager.send_message()
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )
    await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that ChatUserMessage record was added to the DB
    async with async_session_maker() as session:
        res = await session.scalars(
            select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
        )
        messages = res.all()
    assert len(messages) == 1
    assert messages[0].text == message.text


async def test_send_message_success_added_to_message_queue(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of send_message() adds a message to the message broker's queue
    """
    # Create User, Chat, UserChatLink
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
        session.add_all((user, chat, user_chat_link))
        await session.commit()

    # Subscribe other_user to channel of the same chat
    await chat_manager.message_broker.subscribe(
        channel=channel_code("chat", chat_id), user_id=other_user_id
    )

    # Call chat_manager.send_message()
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )
    await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that other_user receives message via message broker
    messages = await chat_manager.message_broker.get_messages(user_id=other_user_id)
    assert len(messages) == 1
    user_message = ChatUserMessageSchema.model_validate_json(messages[0])
    assert user_message.text == message.text


async def test_send_message_wrong_sender(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Calling send_message() with wrong sender_id raises UnauthorizedAction
    """
    # Create User, Chat, UserChatLink
    user_id = uuid.uuid4()
    wrong_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
        session.add_all((user, chat, user_chat_link))
        await session.commit()

    # Call chat_manager.send_message() with wrong sender_id and check that exception
    # is raised
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=wrong_user_id
    )
    with pytest.raises(UnauthorizedAction):
        await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that ChatUserMessage wasn't added to the DB
    async with async_session_maker() as session:
        res = await session.scalars(
            select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
        )
        messages = res.all()
    assert len(messages) == 0


async def test_send_message_user_not_a_chat_member(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Calling send_message() with sender_id who is not a chat member
    raises UnauthorizedAction
    """
    # Create User, Chat
    user_id = uuid.uuid4()
    wrong_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    # Call chat_manager.send_message() with user who is not a chat member and check
    # that exception is raised
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=wrong_user_id
    )
    with pytest.raises(UnauthorizedAction):
        await chat_manager.send_message(current_user_id=user_id, message=message)

    # Check that ChatUserMessage wasn't added to the DB
    async with async_session_maker() as session:
        res = await session.scalars(
            select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
        )
        messages = res.all()
    assert len(messages) == 0


@pytest.mark.parametrize("failure_method", ("add_message",))
async def test_send_message_repo_failure(
    async_session_maker: async_sessionmaker,
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    send_message() raises RepositoryError in case of repository failure
    """
    # Create User and Chat, add User to Chat
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
        session.add_all((user, chat, user_chat_link))
        await session.commit()
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


@pytest.mark.parametrize("failure_method", ("post_message",))
async def test_send_message_message_broker_failure(
    async_session_maker: async_sessionmaker,
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    send_message() raises MessageBrokerError in case of message broker failure
    """
    # Create User and Chat, add User to Chat
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
        session.add_all((user, chat, user_chat_link))
        await session.commit()
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )

    # Patch InMemoryMessageBroker.{failure_method} method so that it always raises
    # MessageBrokerException
    with patch.object(
        InMemoryMessageBroker,
        failure_method,
        new=Mock(side_effect=MessageBrokerException()),
    ):
        # Call join_chat() and check that it raises MessageBrokerError
        with pytest.raises(MessageBrokerError):
            await chat_manager.send_message(current_user_id=user_id, message=message)
