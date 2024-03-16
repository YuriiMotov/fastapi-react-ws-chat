import uuid
from dataclasses import dataclass

from aio_pika import Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
)

from backend.services.event_broker.abstract_event_broker import AbstractEventBroker


@dataclass
class UserConData:
    channel: AbstractChannel
    exchange: AbstractExchange
    queue: AbstractQueue


class RabbitEventBroker(AbstractEventBroker):

    def __init__(self, connection: AbstractRobustConnection):
        self._connection = connection
        self._con_data: dict[int, UserConData] = {}

    async def _add_con_data(self, user_id: uuid.UUID) -> UserConData:
        con_data = self._con_data.get(user_id.int)
        assert con_data is None, f"con data already exists for user {user_id.int}"

        channel = await self._connection.channel()
        exchange = await channel.declare_exchange("direct", auto_delete=True)
        queue = await channel.declare_queue(name="", exclusive=True)
        con_data = UserConData(channel=channel, exchange=exchange, queue=queue)
        self._con_data[user_id.int] = con_data
        return con_data

    async def _del_con_data(self, user_id: uuid.UUID):
        user_id_int = user_id.int
        assert self._con_data.get(
            user_id_int
        ), f"con data doesn't exists for user {user_id}"

        await self._con_data[user_id_int].channel.close()
        if self._con_data.get(user_id_int):
            self._con_data.pop(user_id_int)

    async def subscribe(self, channel: str, user_id: uuid.UUID):
        con_data = self._con_data.get(user_id.int)
        if con_data is None:
            con_data = await self._add_con_data(user_id)
        routing_key = channel
        await con_data.queue.bind(con_data.exchange, routing_key)

    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        con_data = self._con_data.get(user_id.int)
        if con_data is None:
            con_data = await self._add_con_data(user_id)

        for routing_key in channels:
            await con_data.queue.bind(con_data.exchange, routing_key)

    async def unsubscribe(self, user_id: uuid.UUID):
        assert (
            self._con_data.get(user_id.int) is not None
        ), "supposed that subscribe* is called first"
        await self._del_con_data(user_id)

    async def get_events(self, user_id: uuid.UUID, limit: int = -1) -> list[str]:
        con_data = self._con_data.get(user_id.int)
        assert con_data is not None, "supposed that subscribe* is called first"
        events: list[str] = []
        count = limit if (limit > -1) else 1_000_000
        for _ in range(count):
            message = await con_data.queue.get(fail=False)
            if message:
                events.append(message.body.decode())
            else:
                break
        return events

    async def post_event(self, channel: str, user_id: uuid.UUID, event: str):
        con_data = self._con_data.get(user_id.int)
        assert con_data is not None, "supposed that subscribe* is called first"
        await con_data.exchange.publish(Message(event.encode()), channel)
