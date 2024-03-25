import uuid

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
    def _init(self):
        self.event_broker = InMemoryEventBroker()
        self.event_broker_instance_2 = InMemoryEventBroker()

    async def _post_message(self, routing_key: str, message: str):
        uid = uuid.uuid4()
        async with self.event_broker.session(uid):
            await self.event_broker._post_event_str(channel=routing_key, event=message)
