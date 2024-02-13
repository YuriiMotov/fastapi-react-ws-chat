import uuid
from datetime import datetime

import pytest
from schemas.chat_message import ChatUserMessageSchema
from services.chat_manager.chat_manager import ChatManager
from services.chat_manager.utils import channel_code
from services.message_broker.message_broker_exc import (
    MessageBrokerUserNotSubscribedError,
)


@pytest.mark.parametrize("count", (0, 1, 2))
async def test_get_new_messages(chat_manager: ChatManager, count: int):
    """
    get_new_messages() returns messages from message broker's queue.
    """
    # Subscribe user and add {count} messages to their queue
    user_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    channel = channel_code("chat", chat_id)
    await chat_manager.message_broker.subscribe(channel=channel, user_id=user_id)
    messages = []
    for _ in range(count):
        message = ChatUserMessageSchema(
            id=1,
            dt=datetime.utcnow(),
            chat_id=chat_id,
            text="my message",
            sender_id=another_user_id,
        )
        messages.append(message)
        await chat_manager.message_broker.post_message(
            channel=channel, message=message.model_dump_json()
        )

    # Call chat_manager.get_new_messages_str() and check the results
    messages_res = await chat_manager.get_new_messages_str(current_user_id=user_id)
    assert len(messages_res) == count
    for i in range(count):
        assert messages_res[i] == messages[i].model_dump_json()


async def test_get_new_messages_not_subscribed(chat_manager: ChatManager):
    """
    Calling get_new_messages() with user_id of user that isn't subscribed
    raises MessageBrokerUserNotSubscribedError exception
    """
    user_id = uuid.uuid4()

    with pytest.raises(MessageBrokerUserNotSubscribedError):
        await chat_manager.get_new_messages_str(current_user_id=user_id)
