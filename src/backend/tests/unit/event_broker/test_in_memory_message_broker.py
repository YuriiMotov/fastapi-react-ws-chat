import uuid
from typing import cast

import pytest

from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker
from backend.tests.unit.event_broker.event_broker_test_base import EventBrokerTestBase


class TestInMemoryEventBroker(EventBrokerTestBase):
    """
    Test class for InMemoryEventBroker
    (concrete implementation of AbstractEventBroker interface).

    Test methods are implemented in the base test class (EventBrokerTestBase).
    """

    @pytest.fixture(autouse=True)
    def _create_event_broker(self):
        self.event_broker = InMemoryEventBroker()

    async def _check_subscribed(self, user_id: uuid.UUID, channel: str) -> bool:
        event_broker = cast(InMemoryEventBroker, self.event_broker)
        return str(user_id) in event_broker._subscribtions[channel]

    async def _get_events(self, user_id: uuid.UUID) -> list[str]:
        event_broker = cast(InMemoryEventBroker, self.event_broker)
        return list(event_broker._event_queue[str(user_id)])
