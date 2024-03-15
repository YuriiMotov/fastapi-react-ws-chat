import uuid

from backend.services.chat_manager.utils import channel_code
from backend.services.event_broker.abstract_event_broker import AbstractEventBroker


class EventBrokerTestBase:
    """
    Base class for testing concrete implementations of AbstractEventBroker interface.

    To add tests for a concrete class:
     - create a descendant class from EventBrokerTestBase
     - implement abstract methods (_create_event_broker, _post_message)
    """

    # async def test_subscribe(self):
    #     """
    #     subscribe() method subscribes user for new events in specific channel
    #     """
    #     user_id = uuid.uuid4()
    #     channel = channel_code("chat", uuid.uuid4())

    #     # Subscribe user to channel
    #     await self.event_broker.subscribe(channel=channel, user_id=user_id)

    #     # Check that user was subscribed
    #     assert (await self._check_subscribed(user_id=user_id, channel=channel)) is
    # True

    # async def test_subscribe_several_users(self):
    #     """
    #     subscribe() method subscribes user for new events in specific channel.
    #     Making shure that it works for several users.
    #     """
    #     user_id_1 = uuid.uuid4()
    #     user_id_2 = uuid.uuid4()
    #     channel = channel_code("chat", uuid.uuid4())

    #     # Subscribe both users to channel
    #     await self.event_broker.subscribe(channel=channel, user_id=user_id_1)
    #     await self.event_broker.subscribe(channel=channel, user_id=user_id_2)

    #     # Check that both users were subscribed
    #     assert (
    #         await self._check_subscribed(user_id=user_id_1, channel=channel)
    #     ) is True
    #     assert (
    #         await self._check_subscribed(user_id=user_id_2, channel=channel)
    #     ) is True

    # async def test_subscribe_list(self):
    #     """
    #     subscribe_list() method subscribes user for new events in all channel from
    #     the list.
    #     """
    #     user_id = uuid.uuid4()
    #     channel_1 = channel_code("chat", uuid.uuid4())
    #     channel_2 = channel_code("chat", uuid.uuid4())

    #     # Subscribe user for two channels
    #     await self.event_broker.subscribe_list(
    #         channels=[channel_1, channel_2], user_id=user_id
    #     )

    #     # Check that user was subscribed for both channels
    #     assert (
    #         await self._check_subscribed(user_id=user_id, channel=channel_1)
    #     ) is True
    #     assert (
    #         await self._check_subscribed(user_id=user_id, channel=channel_2)
    #     ) is True

    # async def test_unsubscribe(self):
    #     """
    #     unsubscribe() method unsubscribes specific user from all channels
    #     """
    #     user_id = uuid.uuid4()
    #     channel_1 = channel_code("chat", uuid.uuid4())
    #     channel_2 = channel_code("chat", uuid.uuid4())

    #     # Subscribe user to channel
    #     await self.event_broker.subscribe_list(
    #         channels=[channel_1, channel_2], user_id=user_id
    #     )

    #     # Unsubscribe user from channel
    #     await self.event_broker.unsubscribe(user_id=user_id)

    #     # Check that is not subscribed anymore
    #     assert (
    #         await self._check_subscribed(user_id=user_id, channel=channel_1)
    #     ) is False
    #     assert (
    #         await self._check_subscribed(user_id=user_id, channel=channel_2)
    #     ) is False

    async def test_subscribe_post_receive__success(self):
        """
        user_1 subscribes to the channel, user_2 posts a message to the channel, user_1
        receives the message
        """
        user_1_event_broker = await self._create_event_broker()
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = "my event"

        # Subcribe user_1 to channel
        await user_1_event_broker.subscribe(channel=channel, user_id=user_id_1)

        # Post event to channel
        await self._post_message(routing_key=channel, message=event)

        # Check that event was added to user_1's queue
        user_1_events = await user_1_event_broker.get_events(user_id_1)
        assert len(user_1_events) == 1
        assert user_1_events[0] == event

    async def test_post_subscribe_receive__empty(self):
        """
        user_2 posts a message to the channel, then user_1 subscribes to the channel,
        user_1 shouldn't receive the message, because it was posted before they
        subscribed
        """
        user_1_event_broker = await self._create_event_broker()
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = "my event"

        # Post event to channel
        await self._post_message(routing_key=channel, message=event)

        # Subcribe user_1 to channel
        await user_1_event_broker.subscribe(channel=channel, user_id=user_id_1)

        # Check that event was added to user_1's queue
        user_1_events = await user_1_event_broker.get_events(user_id_1)
        assert len(user_1_events) == 0

    # async def test_post_event_unsubscribed(self):
    #     """
    #     post_event() method doesn't add event to unsubscribed user's queue
    #     """
    #     user_id = uuid.uuid4()
    #     channel = channel_code("chat", uuid.uuid4())
    #     event = "my event"

    #     # Subscribe user to channel and then unsubscribe them from all channels
    #     await self.event_broker.subscribe(channel=channel, user_id=user_id)
    #     await self.event_broker.unsubscribe(user_id=user_id)

    #     # Post event to channel
    #     await self.event_broker.post_event(channel=channel, event=event)

    #     # Check that event wasn't added to user's queue
    #     user_1_events = await self._get_events(user_id)
    #     assert len(user_1_events) == 0

    # async def test_post_event_before_subscription(self):
    #     """
    #     post_event() method doesn't add event to the queue of user who subscribed
    #     to the channel after event was posted
    #     """
    #     user_id = uuid.uuid4()
    #     channel = channel_code("chat", uuid.uuid4())
    #     event = "my event"

    #     # Post event to the channel
    #     await self.event_broker.post_event(channel=channel, event=event)

    #     # Subscribe user to the channel
    #     await self.event_broker.subscribe(channel=channel, user_id=user_id)

    #     # Check that event wasn't added to user's queue
    #     user_1_events = await self._get_events(user_id)
    #     assert len(user_1_events) == 0

    # async def test_get_events_one(self):
    #     """
    #     get_events() method returns event from user's queue
    #     """
    #     user_id = uuid.uuid4()
    #     channel = channel_code("chat", uuid.uuid4())
    #     event = "my event"

    #     # Subscribe user to the channel
    #     await self.event_broker.subscribe(channel=channel, user_id=user_id)

    #     # Post event to the channel
    #     await self.event_broker.post_event(channel=channel, event=event)

    #     # Check that get_events() returns posted event
    #     events = await self.event_broker.get_events(user_id)
    #     assert len(events) == 1
    #     assert events[0] == event

    # async def test_get_events_several_channels_fifo(self):
    #     """
    #     get_events() method returns events from user's queue.

    #     User subscribed to several channels and events were posted to different
    #     channels
    #     """
    #     user_id = uuid.uuid4()
    #     channel_1 = channel_code("chat", uuid.uuid4())
    #     channel_2 = channel_code("chat", uuid.uuid4())
    #     channel_3 = channel_code("chat", uuid.uuid4())
    #     event_1 = "my event 1"
    #     event_2 = "my event 2"
    #     event_3 = "my event 3"

    #     # Subscribe user to channels 1 and 2. Don't subscribe them to channel 3!
    #     await self.event_broker.subscribe_list(
    #         channels=[channel_1, channel_2], user_id=user_id
    #     )

    #     # Post event to all 3 channels
    #     await self.event_broker.post_event(channel=channel_1, event=event_1)
    #     await self.event_broker.post_event(channel=channel_2, event=event_2)
    #     await self.event_broker.post_event(channel=channel_3, event=event_3)

    #     # Check that get_events() returns all events from channels
    #     # user subscribed to
    #     events = await self.event_broker.get_events(user_id)
    #     assert len(events) == 2
    #     assert events[0] == event_1
    #     assert events[1] == event_2

    # Methods below should be implemented in the descendant class

    async def _create_event_broker(self) -> AbstractEventBroker:
        raise NotImplementedError

    async def _post_message(self, routing_key: str, message: str):
        raise NotImplementedError
