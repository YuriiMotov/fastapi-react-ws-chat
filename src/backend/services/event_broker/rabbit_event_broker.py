import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator

from aio_pika import Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
)

from backend.services.event_broker.abstract_event_broker import (
    USE_CONTEXT_ERROR,
    AbstractEventBroker,
)

USE_AINIT_ERROR = (
    "RabbitEventBroker should be initialized by calling `await event_broker.ainit()` "
    "before using"
)


@dataclass
class UserConData:
    channel: AbstractChannel
    exchange: AbstractExchange
    queue: AbstractQueue


class RabbitEventBroker(AbstractEventBroker):

    def __init__(self, connection: AbstractRobustConnection):
        self._connection = connection
        self._con_data: dict[int, UserConData] = {}
        self._common_channel: AbstractChannel | None = None
        self._common_exchange: AbstractExchange | None = None

    async def ainit(self):
        self._common_channel = await self._connection.channel()
        self._common_exchange = await self._common_channel.declare_exchange(
            "direct", auto_delete=True
        )

    @asynccontextmanager
    async def session(self, user_id: uuid.UUID) -> AsyncIterator[None]:
        user_id_int = user_id.int
        con_data = self._con_data.get(user_id_int)
        assert con_data is None, f"session already exists for user {user_id_int}"
        channel = await self._connection.channel()
        exchange = await channel.declare_exchange("direct", auto_delete=True)
        queue = await channel.declare_queue(name="", exclusive=True)
        con_data = UserConData(channel=channel, exchange=exchange, queue=queue)
        self._con_data[user_id.int] = con_data
        yield
        assert self._con_data.get(
            user_id_int
        ), f"con data doesn't exists for user {user_id}"
        await self._con_data[user_id_int].channel.close()
        if self._con_data.get(user_id_int):
            self._con_data.pop(user_id_int)

    async def subscribe(self, channel: str, user_id: uuid.UUID):
        con_data = self._con_data.get(user_id.int)
        assert con_data is not None, USE_CONTEXT_ERROR
        routing_key = channel
        await con_data.queue.bind(con_data.exchange, routing_key)

    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        con_data = self._con_data.get(user_id.int)
        assert con_data is not None, USE_CONTEXT_ERROR
        for routing_key in channels:
            await con_data.queue.bind(con_data.exchange, routing_key)

    async def get_events(
        self, user_id: uuid.UUID, limit: int | None = None
    ) -> list[str]:
        con_data = self._con_data.get(user_id.int)
        assert con_data is not None, USE_CONTEXT_ERROR
        events: list[str] = []
        count = limit if (limit is not None) else 1_000_000
        for _ in range(count):
            message = await con_data.queue.get(fail=False)
            if message:
                events.append(message.body.decode())
            else:
                break
        return events

    async def post_event(self, channel: str, event: str):
        assert self._common_exchange is not None, USE_AINIT_ERROR
        await self._common_exchange.publish(Message(event.encode()), channel)
