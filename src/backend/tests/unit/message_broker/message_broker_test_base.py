import uuid
from services.message_broker.abstract_message_broker import AbstractMessageBroker


class MessageBrokerTestBase:
    message_broker: AbstractMessageBroker

    async def test_subscribe(self):
        user_id = uuid.uuid4()
        channel = f"chat_{uuid.uuid4()}"
        await self.message_broker.subscribe(channel=channel, user_id=user_id)
        assert (await self._check_subscribed(user_id=user_id, channel=channel)) == True

    async def test_subscribe_several_users(self):
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        channel = f"chat_{uuid.uuid4()}"
        await self.message_broker.subscribe(channel=channel, user_id=user_id_1)
        await self.message_broker.subscribe(channel=channel, user_id=user_id_2)

        assert (
            await self._check_subscribed(user_id=user_id_1, channel=channel)
        ) == True
        assert (
            await self._check_subscribed(user_id=user_id_2, channel=channel)
        ) == True

    async def test_subscribe_list(self):
        user_id = uuid.uuid4()
        channel_1 = f"chat_{uuid.uuid4()}"
        channel_2 = f"chat_{uuid.uuid4()}"
        await self.message_broker.subscribe_list(
            channels=[channel_1, channel_2], user_id=user_id
        )
        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_1)
        ) == True
        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_2)
        ) == True

    async def test_unsubscribe(self):
        user_id = uuid.uuid4()
        channel_1 = f"chat_{uuid.uuid4()}"
        channel_2 = f"chat_{uuid.uuid4()}"
        await self.message_broker.subscribe_list(
            channels=[channel_1, channel_2], user_id=user_id
        )
        await self.message_broker.unsubscribe(user_id=user_id)

        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_1)
        ) == False
        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_2)
        ) == False

    async def test_post_message(self):
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        channel = f"chat_{uuid.uuid4()}"
        message = "my message"
        await self.message_broker.subscribe(channel=channel, user_id=user_id_1)
        await self.message_broker.subscribe(channel=channel, user_id=user_id_2)

        await self.message_broker.post_message(channel=channel, message=message)

        user_1_messages = await self._get_messages(user_id_1)
        user_2_messages = await self._get_messages(user_id_2)
        assert len(user_1_messages) == 1
        assert len(user_2_messages) == 1
        assert user_1_messages[0] == message
        assert user_2_messages[0] == message

    async def test_get_messages_one(self):
        user_id = uuid.uuid4()
        channel = f"chat_{uuid.uuid4()}"
        message = "my message"
        await self.message_broker.subscribe(channel=channel, user_id=user_id)
        await self.message_broker.post_message(channel=channel, message=message)
        messages = await self.message_broker.get_messages(user_id)
        assert len(messages) == 1
        assert messages[0] == message

    async def test_get_messages_several_channels_fifo(self):
        user_id = uuid.uuid4()
        channel_1 = f"chat_{uuid.uuid4()}"
        channel_2 = f"chat_{uuid.uuid4()}"
        message_1 = "my message 1"
        message_2 = "my message 2"
        await self.message_broker.subscribe_list(
            channels=[channel_1, channel_2], user_id=user_id
        )
        await self.message_broker.post_message(channel=channel_1, message=message_1)
        await self.message_broker.post_message(channel=channel_2, message=message_2)
        messages = await self.message_broker.get_messages(user_id)
        assert len(messages) == 2
        assert messages[0] == message_1
        assert messages[1] == message_2

    # Methods below should be implemented in concreet MessageBrokerTest classes

    async def _check_subscribed(self, user_id: uuid.UUID, channel: str) -> bool:
        raise NotImplementedError

    async def _get_messages(self, user_id: uuid.UUID) -> list[str]:
        raise NotImplementedError
