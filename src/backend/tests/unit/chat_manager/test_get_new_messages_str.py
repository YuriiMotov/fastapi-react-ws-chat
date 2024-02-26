import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from backend.schemas.chat_message import ChatUserMessageSchema
from backend.schemas.event import ChatMessageEvent
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    MessageBrokerError,
    NotSubscribedError,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.message_broker.in_memory_message_broker import (
    InMemoryMessageBroker,
)
from backend.services.message_broker.message_broker_exc import MessageBrokerException


@pytest.mark.parametrize("count", (0, 1, 2))
async def test_get_new_messages_str(chat_manager: ChatManager, count: int):
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
            channel=channel, message=ChatMessageEvent(message=message).model_dump_json()
        )

    # Call chat_manager.get_new_messages_str() and check the results
    messages_res = await chat_manager.get_new_messages_str(current_user_id=user_id)
    assert len(messages_res) == count
    for i in range(count):
        assert messages[i].model_dump_json() in messages_res[i]


async def test_get_new_messages_str_not_subscribed(chat_manager: ChatManager):
    """
    Calling get_new_messages() with user_id of user that isn't subscribed
    raises NotSubscribedError exception
    """
    user_id = uuid.uuid4()

    with pytest.raises(NotSubscribedError):
        await chat_manager.get_new_messages_str(current_user_id=user_id)


# @pytest.mark.parametrize("failure_method", (,))
# async def test_get_new_messages_str_repo_failure(
#     chat_manager: ChatManager, failure_method: str
# ):
#     """
#     get_new_messages() raises RepositoryError in case of repository failure
#     """
#     user_id = uuid.uuid4()

#     # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
#     # ChatRepoException
#     with patch.object(
#         SQLAlchemyChatRepo,
#         failure_method,
#         new=Mock(side_effect=ChatRepoException()),
#     ):
#         # Call join_chat() and check that it raises RepositoryError
#         with pytest.raises(RepositoryError):
#             await chat_manager.get_new_messages_str(current_user_id=user_id)


@pytest.mark.parametrize("failure_method", ("get_messages",))
async def test_get_new_messages_str_message_bus_failure(
    chat_manager: ChatManager, failure_method: str
):
    """
    get_new_messages() raises MessageBrokerError in case of message broker failure
    """
    user_id = uuid.uuid4()

    # Patch InMemoryMessageBroker.{failure_method} method so that it always raises
    # MessageBrokerException
    with patch.object(
        InMemoryMessageBroker,
        failure_method,
        new=Mock(side_effect=MessageBrokerException()),
    ):
        # Call join_chat() and check that it raises MessageBrokerError
        with pytest.raises(MessageBrokerError):
            await chat_manager.get_new_messages_str(current_user_id=user_id)
