import uuid
import pytest
from sqlalchemy import select

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from schemas.chat_message import ChatUserMessageCreateSchema
from models.chat_message import ChatUserMessage
from services.chat_manager.chat_manager_exc import (
    ChatManagerException,
    UnauthorizedAction,
)
from models.chat import Chat
from models.user import User
from models.user_chat_link import UserChatLink

from services.chat_manager.chat_manager import ChatManager


async def test_send_message_success(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
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
    await chat_manager.send_message(current_user_id=user_id, message=message)

    async with async_session_maker() as session:
        res = await session.scalars(
            select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
        )
        messages = res.all()
    assert len(messages) == 1
    assert messages[0].text == message.text


async def test_send_message_wrong_sender(
    async_session_maker: async_sessionmaker, chat_manager: ChatManager
):
    user_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    session: AsyncSession
    async with async_session_maker() as session:
        chat = Chat(id=chat_id, title="", owner_id=uuid.uuid4())
        user = User(id=user_id, name="")
        user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
        session.add_all((user, chat, user_chat_link))
        await session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=another_user_id
    )
    with pytest.raises(UnauthorizedAction):
        await chat_manager.send_message(current_user_id=user_id, message=message)

    async with async_session_maker() as session:
        res = await session.scalars(
            select(ChatUserMessage).where(ChatUserMessage.chat_id == chat_id)
        )
        messages = res.all()
    assert len(messages) == 0
