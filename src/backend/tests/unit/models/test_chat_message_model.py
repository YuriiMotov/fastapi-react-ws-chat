import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models.chat_message import ChatNotification, ChatUserMessage


async def test_insert_user_message(async_session: AsyncSession):
    um = ChatUserMessage(
        chat_id=uuid.uuid4(),
        text="my message",
        sender_id=uuid.uuid4(),
    )
    async_session.add(um)
    await async_session.commit()
    await async_session.refresh(um)

    assert um.id is not None
    assert um.id > 0
    assert um.is_notification is False


async def test_insert_user_message_null_sender(async_session: AsyncSession):
    um = ChatUserMessage(
        chat_id=uuid.uuid4(),
        text="my message",
        sender_id=None,
    )
    async_session.add(um)
    with pytest.raises(SQLAlchemyError):
        await async_session.commit()


async def test_insert_notification(async_session: AsyncSession):
    notification = ChatNotification(
        chat_id=uuid.uuid4(),
        text="my notification",
        params=str(uuid.uuid4()),
    )
    async_session.add(notification)
    await async_session.commit()
    await async_session.refresh(notification)

    assert notification.id is not None
    assert notification.id > 0
    assert notification.is_notification is True
    assert notification.text == "my notification"
    assert notification.params is not None
