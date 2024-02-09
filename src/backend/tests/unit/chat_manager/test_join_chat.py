import uuid
import pytest
from sqlalchemy import select

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from models.chat_message import ChatNotification
from services.chat_manager.chat_manager_exc import ChatManagerException
from services.uow.sqla_uow import SQLAlchemyUnitOfWork
from models.chat import Chat
from models.user import User
from models.user_chat_link import UserChatLink

from services.chat_manager.chat_manager import (
    USER_JOINED_CHAT_NOTIFICATION,
    ChatManager,
)


async def test_join_chat_success(async_session_maker: async_sessionmaker):
    chat_manager = ChatManager(SQLAlchemyUnitOfWork(async_session_maker))
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    await chat_manager.join_chat(
        current_user_id=user_id, user_id=user_id, chat_id=chat_id
    )

    async with async_session_maker() as session:
        user_chat_link = await session.scalar(
            select(UserChatLink)
            .where(UserChatLink.chat_id == chat_id)
            .where(UserChatLink.user_id == user_id)
        )
        assert user_chat_link is not None


async def test_join_chat_notification_added(async_session_maker: async_sessionmaker):
    chat_manager = ChatManager(SQLAlchemyUnitOfWork(async_session_maker))
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        session.add_all((user, chat))
        await session.commit()

    await chat_manager.join_chat(
        current_user_id=user_id, user_id=user_id, chat_id=chat_id
    )

    async with async_session_maker() as session:
        res = await session.scalars(
            select(ChatNotification).where(ChatNotification.chat_id == chat_id)
        )
        notifications = res.all()
    assert len(notifications) == 1
    assert notifications[0].text == USER_JOINED_CHAT_NOTIFICATION
    assert notifications[0].params == str(user_id)
