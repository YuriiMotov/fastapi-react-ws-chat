import uuid

from backend.services.chat_manager.utils import channel_code
from backend.services.message_broker.abstract_message_broker import (
    AbstractMessageBroker,
)


class MessageBrokerTestBase:
    """
    Base class for testing concrete implementations of AbstractMessageBroker interface.

    To add tests for a concrete class:
     - create a descendant class from MessageBrokerTestBase
     - add fixture (with autouse=True) that initializes self.repo with the concrete
        implementation of the AbstractMessageBroker interface
     - implement abstract methods (_check_subscribed, _get_messages, etc..)
    """

    message_broker: AbstractMessageBroker  # Should be initialized by fixture

    async def test_subscribe(self):
        """
        subscribe() method subscribes user for new messages in specific channel
        """
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        # Subscribe user to channel
        await self.message_broker.subscribe(channel=channel, user_id=user_id)

        # Check that user was subscribed
        assert (await self._check_subscribed(user_id=user_id, channel=channel)) is True

    async def test_subscribe_several_users(self):
        """
        subscribe() method subscribes user for new messages in specific channel.
        Making shure that it works for several users.
        """
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        # Subscribe both users to channel
        await self.message_broker.subscribe(channel=channel, user_id=user_id_1)
        await self.message_broker.subscribe(channel=channel, user_id=user_id_2)

        # Check that both users were subscribed
        assert (
            await self._check_subscribed(user_id=user_id_1, channel=channel)
        ) is True
        assert (
            await self._check_subscribed(user_id=user_id_2, channel=channel)
        ) is True

    async def test_subscribe_list(self):
        """
        subscribe_list() method subscribes user for new messages in all channel from
        the list.
        """
        user_id = uuid.uuid4()
        channel_1 = channel_code("chat", uuid.uuid4())
        channel_2 = channel_code("chat", uuid.uuid4())

        # Subscribe user for two channels
        await self.message_broker.subscribe_list(
            channels=[channel_1, channel_2], user_id=user_id
        )

        # Check that user was subscribed for both channels
        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_1)
        ) is True
        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_2)
        ) is True

    async def test_unsubscribe(self):
        """
        unsubscribe() method unsubscribes specific user from all channels
        """
        user_id = uuid.uuid4()
        channel_1 = channel_code("chat", uuid.uuid4())
        channel_2 = channel_code("chat", uuid.uuid4())

        # Subscribe user to channel
        await self.message_broker.subscribe_list(
            channels=[channel_1, channel_2], user_id=user_id
        )

        # Unsubscribe user from channel
        await self.message_broker.unsubscribe(user_id=user_id)

        # Check that is not subscribed anymore
        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_1)
        ) is False
        assert (
            await self._check_subscribed(user_id=user_id, channel=channel_2)
        ) is False

    async def test_post_message(self):
        """
        post_message() method adds message to all subscribed user's queues
        """
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        message = "my message"

        # Subcribe two users to channel
        await self.message_broker.subscribe(channel=channel, user_id=user_id_1)
        await self.message_broker.subscribe(channel=channel, user_id=user_id_2)

        # Post message to channel to channel
        await self.message_broker.post_message(channel=channel, message=message)

        # Check that message was added to both user's queues
        user_1_messages = await self._get_messages(user_id_1)
        user_2_messages = await self._get_messages(user_id_2)
        assert len(user_1_messages) == 1
        assert len(user_2_messages) == 1
        assert user_1_messages[0] == message
        assert user_2_messages[0] == message

    async def test_post_message_unsubscribed(self):
        """
        post_message() method doesn't add message to unsubscribed user's queue
        """
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        message = "my message"

        # Subscribe user to channel and then unsubscribe them from all channels
        await self.message_broker.subscribe(channel=channel, user_id=user_id)
        await self.message_broker.unsubscribe(user_id=user_id)

        # Post message to channel
        await self.message_broker.post_message(channel=channel, message=message)

        # Check that message wasn't added to user's queue
        user_1_messages = await self._get_messages(user_id)
        assert len(user_1_messages) == 0

    async def test_post_message_before_subscription(self):
        """
        post_message() method doesn't add message to the queue of user who subscribed
        to the channel after message was posted
        """
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        message = "my message"

        # Post message to the channel
        await self.message_broker.post_message(channel=channel, message=message)

        # Subscribe user to the channel
        await self.message_broker.subscribe(channel=channel, user_id=user_id)

        # Check that message wasn't added to user's queue
        user_1_messages = await self._get_messages(user_id)
        assert len(user_1_messages) == 0

    async def test_get_messages_one(self):
        """
        get_messages() method returns message from user's queue
        """
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        message = "my message"

        # Subscribe user to the channel
        await self.message_broker.subscribe(channel=channel, user_id=user_id)

        # Post message to the channel
        await self.message_broker.post_message(channel=channel, message=message)

        # Check that get_messages() returns posted message
        messages = await self.message_broker.get_messages(user_id)
        assert len(messages) == 1
        assert messages[0] == message

    async def test_get_messages_several_channels_fifo(self):
        """
        get_messages() method returns messages from user's queue.

        User subscribed to several channels and messages were posted to different
        channels
        """
        user_id = uuid.uuid4()
        channel_1 = channel_code("chat", uuid.uuid4())
        channel_2 = channel_code("chat", uuid.uuid4())
        channel_3 = channel_code("chat", uuid.uuid4())
        message_1 = "my message 1"
        message_2 = "my message 2"
        message_3 = "my message 3"

        # Subscribe user to channels 1 and 2. Don't subscribe them to channel 3!
        await self.message_broker.subscribe_list(
            channels=[channel_1, channel_2], user_id=user_id
        )

        # Post messages to all 3 channels
        await self.message_broker.post_message(channel=channel_1, message=message_1)
        await self.message_broker.post_message(channel=channel_2, message=message_2)
        await self.message_broker.post_message(channel=channel_3, message=message_3)

        # Check that get_messages() returns all messages from channels
        # user subscribed to
        messages = await self.message_broker.get_messages(user_id)
        assert len(messages) == 2
        assert messages[0] == message_1
        assert messages[1] == message_2

    # Methods below should be implemented in the descendant class

    async def _check_subscribed(self, user_id: uuid.UUID, channel: str) -> bool:
        raise NotImplementedError

    async def _get_messages(self, user_id: uuid.UUID) -> list[str]:
        raise NotImplementedError
