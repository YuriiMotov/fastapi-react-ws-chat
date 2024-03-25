import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from backend.schemas.chat_message import ChatUserMessageSchema
from backend.schemas.event import ChatMessageEvent
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    EventBrokerError,
    NotSubscribedError,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.event_broker.event_broker_exc import EventBrokerException
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker


@pytest.mark.parametrize("count", (0, 1, 2))
async def test_get_events_str(
    chat_manager: ChatManager,
    count: int,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    get_events_str() returns events from Event broker's queue.
    """
    # Subscribe user and add {count} messages to their queue
    user_id = event_broker_user_id_list[0]
    another_user_id = event_broker_user_id_list[1]
    chat_id = uuid.uuid4()
    channel = channel_code("chat", chat_id)
    await chat_manager.event_broker.subscribe(channel=channel, user_id=user_id)
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
        await chat_manager.event_broker.post_event_str(
            channel=channel,
            event=ChatMessageEvent(message=message).model_dump_json(),
        )

    # Call chat_manager.get_events_str() and check the results
    events_res = await chat_manager.get_events_str(current_user_id=user_id)
    assert len(events_res) == count
    for i in range(count):
        assert messages[i].model_dump_json() in events_res[i]


@pytest.mark.xfail
async def test_get_events_str_not_subscribed(
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    Calling get_events_str() with user_id of user that isn't subscribed
    raises NotSubscribedError exception
    """
    user_id = event_broker_user_id_list[0]
    with pytest.raises(NotSubscribedError):
        await chat_manager.get_events_str(current_user_id=user_id)


@pytest.mark.parametrize("failure_method", ("get_events_str",))
async def test_get_events_str_event_bus_failure(
    chat_manager: ChatManager, failure_method: str
):
    """
    get_events_str() raises EventBrokerError in case of Event broker failure
    """
    user_id = uuid.uuid4()

    # Patch InMemoryEventBroker.{failure_method} method so that it always raises
    # EventBrokerException
    with patch.object(
        InMemoryEventBroker,
        failure_method,
        new=Mock(side_effect=EventBrokerException()),
    ):
        # Call get_events_str() and check that it raises EventBrokerError
        with pytest.raises(EventBrokerError):
            await chat_manager.get_events_str(current_user_id=user_id)
