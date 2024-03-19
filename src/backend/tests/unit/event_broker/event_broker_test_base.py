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

    event_broker: AbstractEventBroker
    event_broker_instance_2: AbstractEventBroker

    async def test_get_events__subscribe_post_receive__success(self):
        """
        user_1 subscribes to the channel, user_2 posts a message to the channel, user_1
        receives the message
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = "my event"

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Post event to channel
            await self._post_message(routing_key=channel, message=event)

            # Check that event was added to user_1's queue
            user_1_events = await self.event_broker.get_events(user_id_1)
            assert len(user_1_events) == 1
            assert user_1_events[0] == event

    async def test_get_events__post_before_subscribe__empty_result(self):
        """
        user_2 posts a message to the channel, then user_1 subscribes to the channel,
        user_1 shouldn't receive the message, because it was posted before they
        subscribed
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = "my event"

        async with self.event_broker.session(user_id_1):
            # Post event to channel
            await self._post_message(routing_key=channel, message=event)

            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Check that event was added to user_1's queue
            user_1_events = await self.event_broker.get_events(user_id_1)
            assert len(user_1_events) == 0

    async def test_unsubscribe__post_when_unsubscribed__empty_result(self):
        """
        user_1 subscribes to a channel, then unsubscribes.
        user_2 posts a message to the channel.
        user_1 subscribes to the channel again,
        user_1 shouldn't receive the message, because it was posted before they
        subscribed
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = "my event"

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel and then unsubscribe (exit context manager)
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

        async with self.event_broker.session(user_id_1):
            # Post event to channel
            await self._post_message(routing_key=channel, message=event)

            # Subcribe user_1 to channel again
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Check that event was added to user_1's queue
            user_1_events = await self.event_broker.get_events(user_id_1)
            assert len(user_1_events) == 0

    async def test_unsubscribe__queue_is_cleared(self):
        """
        user_1 subscribes to a channel.
        user_2 posts a message to the channel.
        user_1 unsubscribes and subscribes to the channel again,
        user_1 shouldn't receive the message, because queue should be cleared on
        subscribe
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = "my event"

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Post event to channel
            await self._post_message(routing_key=channel, message=event)

        # Unsubcribe user_1 (exit context manager) and then subscribe again
        async with self.event_broker.session(user_id_1):
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Check that event was added to user_1's queue
            user_1_events = await self.event_broker.get_events(user_id_1)
            assert len(user_1_events) == 0

    async def test_get_events__several_events_fifo__success(self):
        """
        get_events() method returns events from user's queue in right order (FIFO)
        """
        events = ["my event 1", "my event 2", "my event 3"]
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event to the channel
            for event in events:
                await self._post_message(routing_key=channel, message=event)

            # Check that get_events() returns posted event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == len(events)
            assert events_res == events

    async def test_get_events__several_channels_fifo(self):
        """
        get_events() method returns events from user's queue.

        User subscribed to several channels and events were posted to different
        channels
        """
        user_id = uuid.uuid4()
        channel_1 = channel_code("chat", uuid.uuid4())
        channel_2 = channel_code("chat", uuid.uuid4())
        channel_3 = channel_code("chat", uuid.uuid4())
        event_1 = "my event 1"
        event_2 = "my event 2"
        event_3 = "my event 3"

        async with self.event_broker.session(user_id):
            # Subscribe user to channels 1 and 2. Don't subscribe them to channel 3!
            await self.event_broker.subscribe_list(
                channels=[channel_1, channel_2], user_id=user_id
            )

            # Post event to all 3 channels
            await self._post_message(routing_key=channel_1, message=event_1)
            await self._post_message(routing_key=channel_2, message=event_2)
            await self._post_message(routing_key=channel_3, message=event_3)

            # Check that get_events() returns all events from channels
            # user subscribed to
            events = await self.event_broker.get_events(user_id)
            assert len(events) == 2
            assert events[0] == event_1
            assert events[1] == event_2

    async def test_post_event__several_subscribers(self):
        """
        post_event() method posts message to subscribed user's queue
        """
        event = "my event"
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        user_id_3 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        another_channel = channel_code("chat", uuid.uuid4())

        async with (
            self.event_broker.session(user_id_1),
            self.event_broker.session(user_id_2),
            self.event_broker.session(user_id_3),
        ):
            # Subscribe user_1 and user_2 to the channel. Don't subscribe user_3!
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)
            await self.event_broker.subscribe(channel=channel, user_id=user_id_2)

            # Subscribe user_3 to another channel
            await self.event_broker.subscribe(
                channel=another_channel, user_id=user_id_3
            )

            # Post event to the channel
            await self.event_broker.post_event(
                channel=channel, user_id=user_id_1, event=event
            )

            # Check that get_events() returns posted event for user_1 and user_2
            events_res_1 = await self.event_broker.get_events(user_id_1)
            assert len(events_res_1) == 1
            assert events_res_1[0] == event
            events_res_2 = await self.event_broker.get_events(user_id_2)
            assert len(events_res_2) == 1
            assert events_res_2[0] == event

            # Check that get_event() returns empty list for user_3
            events_res_3 = await self.event_broker.get_events(user_id_3)
            assert len(events_res_3) == 0

    async def test_different_instances_work_together(self):
        """
        Post the event using instance #1 of EventBroker, and receive that event using
        instance #2
        """
        event = "my event"
        user_id_1 = uuid.uuid4()
        user_id_2 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with (
            self.event_broker.session(user_id_1),
            self.event_broker_instance_2.session(user_id_2),
        ):
            # Subscribe user_1 and user_2 to the channel.
            # user_1 uses instance #1, user_2 uses instance #2 of EventBroker
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)
            await self.event_broker_instance_2.subscribe(
                channel=channel, user_id=user_id_2
            )

            # Post event to the channel using instance #1 of EventBroker
            await self.event_broker.post_event(
                channel=channel, user_id=user_id_1, event=event
            )

            # Check that get_events() returns posted event for user_1 (instance #1 of
            # EventBroker) and user_2 (instance #2 of EventBroker)
            events_res_1 = await self.event_broker.get_events(user_id_1)
            assert len(events_res_1) == 1
            assert events_res_1[0] == event
            events_res_2 = await self.event_broker_instance_2.get_events(user_id_2)
            assert len(events_res_2) == 1
            assert events_res_2[0] == event

    # Methods below should be implemented in the descendant class

    async def _post_message(self, routing_key: str, message: str):
        raise NotImplementedError
