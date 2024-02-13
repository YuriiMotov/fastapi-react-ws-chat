import uuid

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
from backend.services.chat_manager.utils import channel_code


async def test_join_chat_success(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of join_chat() creates a user-chat
    association record in the database.
    """
    # Create User and Chat
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    # Call chat_manager.join_chat()
    await chat_manager.join_chat(
        current_user_id=user_id, user_id=user_id, chat_id=chat_id
    )

    # Check that UserChatLink record was added to the DB
    async with async_session_maker() as session:
        user_chat_link = await session.scalar(
            select(UserChatLink)
            .where(UserChatLink.chat_id == chat_id)
            .where(UserChatLink.user_id == user_id)
        )
        assert user_chat_link is not None


async def test_join_chat_notification_added_to_db(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of join_chat() creates a notification
    record in the database.
    """
    # Create User and Chat
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    # Call chat_manager.join_chat()
    await chat_manager.join_chat(
        current_user_id=user_id, user_id=user_id, chat_id=chat_id
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


async def test_join_chat_notification_posted_to_mb(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    """
    Successful execution of join_chat() posts a notification
    record to the message broker.
    """
    # Create User and Chat, subscribe user for updates
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()
    await chat_manager.message_broker.subscribe(
        channel=channel_code("chat", chat_id), user_id=other_user_id
    )

    # Call chat_manager.join_chat()
    await chat_manager.join_chat(
        current_user_id=user_id, user_id=user_id, chat_id=chat_id
    )

    # Check that notification message was posted
    chat_messages = await chat_manager.message_broker.get_messages(
        user_id=other_user_id
    )
    assert len(chat_messages) == 1
    notification = ChatNotificationSchema.model_validate_json(chat_messages[0])
    assert notification.text == USER_JOINED_CHAT_NOTIFICATION
    assert notification.params == str(user_id)
