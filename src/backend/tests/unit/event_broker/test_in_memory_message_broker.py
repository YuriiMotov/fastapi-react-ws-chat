import uuid

import pytest

from backend.services.event_broker.abstract_event_broker import AbstractEventBroker
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker
from backend.tests.unit.event_broker.event_broker_test_base import EventBrokerTestBase


class TestInMemoryEventBroker(EventBrokerTestBase):
    """
    Test class for InMemoryEventBroker
    (concrete implementation of AbstractEventBroker interface).

    Test methods are implemented in the base test class (EventBrokerTestBase).
    """

    @pytest.fixture(autouse=True)
    def _init(self):
        self._event_broker = InMemoryEventBroker()

    async def _create_event_broker(self) -> AbstractEventBroker:
        return self._event_broker

    async def _post_message(self, routing_key: str, message: str):
        await self._event_broker.post_event(
            channel=routing_key, user_id=uuid.uuid4(), event=message
        )
