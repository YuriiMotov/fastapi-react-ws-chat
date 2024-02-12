from datetime import datetime
import uuid
import pytest

from services.message_broker.abstract_message_broker import UserNotSubscribed
from schemas.chat_message import ChatUserMessageSchema

from services.chat_manager.chat_manager import ChatManager


async def test_get_messages(chat_manager: ChatManager):
    user_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    channel = f"chat_{chat_id}"

    message = ChatUserMessageSchema(
        id=1,
        dt=datetime.utcnow(),
        chat_id=chat_id,
        text="my message",
        sender_id=another_user_id,
    )
    await chat_manager.message_broker.subscribe(channel=channel, user_id=user_id)
    await chat_manager.message_broker.post_message(
        channel=channel, message=message.model_dump_json()
    )

    messages = await chat_manager.get_new_messages_str(current_user_id=user_id)

    assert len(messages) == 1
    assert messages[0] == message.model_dump_json()


async def test_get_messages_empty(chat_manager: ChatManager):
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    channel = f"chat_{chat_id}"

    await chat_manager.message_broker.subscribe(channel=channel, user_id=user_id)

    messages = await chat_manager.get_new_messages_str(current_user_id=user_id)

    assert len(messages) == 0


async def test_get_messages_not_subscribed(chat_manager: ChatManager):
    user_id = uuid.uuid4()

    with pytest.raises(UserNotSubscribed):
        await chat_manager.get_new_messages_str(current_user_id=user_id)
