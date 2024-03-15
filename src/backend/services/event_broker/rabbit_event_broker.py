import uuid

from aio_pika import Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
)

from backend.services.event_broker.abstract_event_broker import AbstractEventBroker


class RabbitEventBroker(AbstractEventBroker):

    def __init__(self, connection: AbstractRobustConnection):
        self._connection = connection
        self._initialized = False
        self._channel: AbstractChannel
        self._exchange: AbstractExchange
        self._queue: AbstractQueue

    async def _initialize(self, queue_name: str):
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            "direct", auto_delete=True
        )
        self._queue = await self._channel.declare_queue(name=queue_name, exclusive=True)
        await self._queue.purge()
        self._initialized = True

    async def _deinitialize(self):
        await self._channel.close()
        self._initialized = False

    async def subscribe(self, channel: str, user_id: uuid.UUID):
        if not self._initialized:
            await self._initialize(user_id.hex)
        routing_key = channel
        await self._queue.bind(self._exchange, routing_key)

    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        if not self._initialized:
            await self._initialize(user_id.hex)
        for routing_key in channels:
            await self._queue.bind(self._exchange, routing_key)

    async def unsubscribe(self, user_id: uuid.UUID):
        assert self._initialized, "supposed that subscribe* is called first"
        await self._deinitialize()

    async def get_events(self, user_id: uuid.UUID, limit: int = -1) -> list[str]:
        assert self._initialized, "supposed that subscribe* is called first"
        events: list[str] = []
        count = limit if (limit > -1) else 1_000_000
        for _ in range(count):
            message = await self._queue.get(fail=False)
            if message:
                events.append(message.body.decode())
            else:
                break
        return events

    async def post_event(self, channel: str, event: str):
        assert self._initialized, "supposed that subscribe* is called first"
        await self._exchange.publish(Message(event.encode()), channel)
