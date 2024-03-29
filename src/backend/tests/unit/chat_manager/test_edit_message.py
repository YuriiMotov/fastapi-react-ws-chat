import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.event import ChatMessageEdited
from backend.services.chat_manager.chat_manager import ChatManager


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
