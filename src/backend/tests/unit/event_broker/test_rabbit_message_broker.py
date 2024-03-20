import aio_pika
import pytest

from backend.services.event_broker.rabbit_event_broker import RabbitEventBroker
from backend.tests.unit.event_broker.event_broker_test_base import EventBrokerTestBase


class TestRabbitEventBroker(EventBrokerTestBase):
    """
    Test class for RabbitEventBroker
    (concrete implementation of AbstractEventBroker interface).

    Test methods are implemented in the base test class (EventBrokerTestBase).
    """

    @pytest.fixture(autouse=True)
    async def _init(self):
        self._connection = await aio_pika.connect_robust(
            "amqp://guest:guest@127.0.0.1/"
        )
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "direct", auto_delete=True
        )
        self.event_broker = RabbitEventBroker(connection=self._connection)
        await self.event_broker.ainit()

        self._connection_2 = await aio_pika.connect_robust(
            "amqp://guest:guest@127.0.0.1/"
        )
        self.event_broker_instance_2 = RabbitEventBroker(connection=self._connection_2)
        await self.event_broker_instance_2.ainit()

        yield
        await self._connection.close()
        await self._connection_2.close()

    async def _post_message(self, routing_key: str, message: str):
        await self._exchange.publish(aio_pika.Message(message.encode()), routing_key)
