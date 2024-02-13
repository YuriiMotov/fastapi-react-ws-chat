"""
ChatUserMessage and ChatNotification models are implemented using Concrete Table
Inheritance.
https://docs.sqlalchemy.org/en/20/orm/inheritance.html#concrete-table-inheritance

They are both inherited from ChatMessage model.

Here is a list of tests that check whether it works as expected.

"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_message import ChatMessage, ChatNotification, ChatUserMessage


async def test_insert_user_message(async_session: AsyncSession):
    """
    Add ChatUserMessage instance to the DB
    """
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
    """
    Attempt to add ChatUserMessage instance to the DB with wrong sender_id (None)
    raises SQLAlchemyError
    """
    um = ChatUserMessage(
        chat_id=uuid.uuid4(),
        text="my message",
        sender_id=None,  # type: ignore
    )
    async_session.add(um)
    with pytest.raises(SQLAlchemyError):
        await async_session.commit()


async def test_insert_notification(async_session: AsyncSession):
    """
    Add ChatNotification instance to the DB
    """
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


async def test_query_different_types(async_session: AsyncSession):
    """
    Querying ChatUserMessage and ChatNotification objects from DB in one query
    """

    # Add user message and notification to the DB
    notification = ChatNotification(
        chat_id=uuid.uuid4(),
        text="my notification",
        params=str(uuid.uuid4()),
    )
    async_session.add(notification)
    um = ChatUserMessage(
        chat_id=uuid.uuid4(),
        text="my message",
        sender_id=uuid.uuid4(),
    )
    async_session.add(um)
    await async_session.commit()
    await async_session.refresh(notification)
    await async_session.refresh(um)

    # Query user message and notification in one query, check types
    messages = (await async_session.scalars(select(ChatMessage))).all()
    assert len(messages) == 2
    if messages[0].id == notification.id:
        assert isinstance(messages[0], ChatNotification)
        assert isinstance(messages[1], ChatUserMessage)
    else:
        assert isinstance(messages[0], ChatUserMessage)
        assert isinstance(messages[1], ChatNotification)


async def test_query_specific_fields_loaded(async_session: AsyncSession):
    """
    Querying ChatNotification object from DB in one query and
    check that specific fields (specific for ChatNotification model) are loaded.
    """

    # Add notification to the DB
    notification = ChatNotification(
        chat_id=uuid.uuid4(),
        text="my notification",
        params=str(uuid.uuid4()),
    )
    async_session.add(notification)
    await async_session.commit()

    # Query notification object and check that the
    # field `params` (cpecific for ChatNotification model) is loaded
    messages = (await async_session.scalars(select(ChatMessage))).all()
    assert len(messages) == 1
    message = messages[0]
    assert isinstance(message, ChatNotification)
    if isinstance(message, ChatNotification):
        assert message.params == notification.params
