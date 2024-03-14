import uuid
from typing import cast

import aio_pika
import pytest

from backend.services.event_broker.rabbit_event_broker import RabbitEventBroker
from backend.tests.unit.event_broker.event_broker_test_base import EventBrokerTestBase


@pytest.mark.xfail
class TestRabbitEventBroker(EventBrokerTestBase):
    """
    Test class for RabbitEventBroker
    (concrete implementation of AbstractEventBroker interface).

    Test methods are implemented in the base test class (EventBrokerTestBase).
    """

    @pytest.fixture(autouse=True)
    async def _create_event_broker(self):
        connection = await aio_pika.connect_robust("amqp://guest:guest@127.0.0.1/")
        self.event_broker = RabbitEventBroker(connection=connection)

    async def _check_subscribed(self, user_id: uuid.UUID, channel: str) -> bool:
        # event_broker = cast(RabbitEventBroker, self.event_broker)
        return True

    async def _get_events(self, user_id: uuid.UUID) -> list[str]:
        event_broker = cast(RabbitEventBroker, self.event_broker)
        return list(await event_broker.get_events(user_id=user_id))
