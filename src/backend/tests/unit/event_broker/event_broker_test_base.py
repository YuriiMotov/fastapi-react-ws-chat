import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

from backend.schemas.event import (
    AnyEvent,
    ChatMessageEvent,
    UserAddedToChatNotification,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.event_broker.abstract_event_broker import AbstractEventBroker
from backend.services.event_broker.event_broker_exc import (
    EventBrokerException,
    EventBrokerFail,
)
from backend.tests.unit.event_broker.helpers import create_chat_event


class EventBrokerTestBase:
    """
    Base class for testing concrete implementations of AbstractEventBroker interface.

    To add tests for a concrete class:
     - create a descendant class from EventBrokerTestBase
     - implement abstract methods (_create_event_broker, _post_message)
    """

    event_broker: AbstractEventBroker
    event_broker_instance_2: AbstractEventBroker

    @pytest.mark.parametrize(
        "event",
        (
            create_chat_event(ChatMessageEvent),
            create_chat_event(UserAddedToChatNotification),
        ),
    )
    async def test_get_events__subscribe_post_receive__success(self, event: AnyEvent):
        """
        user_1 subscribes to the channel, user_2 posts an event to the channel, user_1
        receives the event
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Post event to channel
            await self._post_message(
                routing_key=channel, message=event.model_dump_json()
            )

            # Check that event was added to user_1's queue
            user_1_events = await self.event_broker.get_events(user_id_1)
            assert len(user_1_events) == 1
            assert type(user_1_events[0]) is type(event)
            assert user_1_events[0].model_dump_json() == event.model_dump_json()

    async def test_get_events__post_before_subscribe__empty_result(self):
        """
        user_2 posts an event to the channel, then user_1 subscribes to the channel,
        user_1 shouldn't receive the event, because it was posted before they
        subscribed
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = create_chat_event(ChatMessageEvent)

        async with self.event_broker.session(user_id_1):
            # Post event to channel
            await self._post_message(
                routing_key=channel, message=event.model_dump_json()
            )

            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Check that event was added to user_1's queue
            user_1_events = await self.event_broker.get_events(user_id_1)
            assert len(user_1_events) == 0

    async def test_unsubscribe__post_when_unsubscribed__empty_result(self):
        """
        user_1 subscribes to a channel, then unsubscribes.
        user_2 posts an event to the channel.
        user_1 subscribes to the channel again,
        user_1 shouldn't receive the event, because it was posted before they
        subscribed
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = create_chat_event(ChatMessageEvent)

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel and then unsubscribe (exit context manager)
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)
        # User_1's event_broker session is exited now

        async with self.event_broker.session(user_id_1):
            # Post event to channel
            await self._post_message(
                routing_key=channel, message=event.model_dump_json()
            )

            # Subcribe user_1 to channel again
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Check that event was added to user_1's queue
            user_1_events = await self.event_broker.get_events(user_id_1)
            assert len(user_1_events) == 0

    async def test_unsubscribe__queue_is_cleared(self):
        """
        user_1 subscribes to a channel.
        user_2 posts an event to the channel.
        user_1 unsubscribes and subscribes to the channel again,
        user_1 shouldn't receive the event, because queue should be cleared on
        subscribe
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = create_chat_event(ChatMessageEvent)

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            # Post event to channel
            await self._post_message(
                routing_key=channel, message=event.model_dump_json()
            )

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
        events = [create_chat_event(ChatMessageEvent) for _ in range(3)]
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event to the channel
            for event in events:
                await self._post_message(
                    routing_key=channel, message=event.model_dump_json()
                )

            # Check that get_events() returns posted event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == len(events)
            assert [ev.model_dump_json() for ev in events_res] == [
                ev.model_dump_json() for ev in events
            ]

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
        event_1 = create_chat_event(ChatMessageEvent)
        event_2 = create_chat_event(ChatMessageEvent)
        event_3 = create_chat_event(ChatMessageEvent)

        async with self.event_broker.session(user_id):
            # Subscribe user to channels 1 and 2. Don't subscribe them to channel 3!
            await self.event_broker.subscribe_list(
                channels=[channel_1, channel_2], user_id=user_id
            )

            # Post event to all 3 channels
            await self._post_message(
                routing_key=channel_1, message=event_1.model_dump_json()
            )
            await self._post_message(
                routing_key=channel_2, message=event_2.model_dump_json()
            )
            await self._post_message(
                routing_key=channel_3, message=event_3.model_dump_json()
            )

            # Check that get_events() returns all events from channels
            # user subscribed to
            events = await self.event_broker.get_events(user_id)
            assert len(events) == 2
            assert events[0].model_dump_json() == event_1.model_dump_json()
            assert events[1].model_dump_json() == event_2.model_dump_json()

    @pytest.mark.parametrize("limit", (None, 1, 2, 10))
    async def test_get_events__limit(self, limit: int | None):
        """
        get_events() method respects `limit` parameter when returns events.
        """
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        events = [create_chat_event(ChatMessageEvent) for i in range(3)]

        async with self.event_broker.session(user_id):
            # Subscribe user to channe
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post events to channel
            for event in events:
                await self._post_message(
                    routing_key=channel, message=event.model_dump_json()
                )

            # Check that get_events() returns event list according to `limit` parameter
            events_res = await self.event_broker.get_events(user_id, limit=limit)
            if limit is None:
                expected_events_res = events
            else:
                expected_events_res = events[:limit]

            assert len(events_res) == len(expected_events_res), events_res
            assert [ev.model_dump_json() for ev in events_res] == [
                ev.model_dump_json() for ev in expected_events_res
            ]

    @pytest.mark.parametrize(
        "event",
        (
            create_chat_event(ChatMessageEvent),
            create_chat_event(UserAddedToChatNotification),
        ),
    )
    async def test_post_event__several_subscribers(self, event: AnyEvent):
        """
        post_event() method posts event to subscribed user's queue
        """
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
            await self.event_broker.post_event(channel=channel, event=event)

            # Check that get_events() returns posted event for user_1 and user_2
            events_res_1 = await self.event_broker.get_events(user_id_1)
            assert len(events_res_1) == 1
            assert type(events_res_1[0]) is type(event)
            assert events_res_1[0].model_dump_json() == event.model_dump_json()
            events_res_2 = await self.event_broker.get_events(user_id_2)
            assert len(events_res_2) == 1
            assert type(events_res_2[0]) is type(event)
            assert events_res_2[0].model_dump_json() == event.model_dump_json()

            # Check that get_event() returns empty list for user_3
            events_res_3 = await self.event_broker.get_events(user_id_3)
            assert len(events_res_3) == 0

    async def test_different_instances_work_together(self):
        """
        Post the event using instance #1 of EventBroker, and receive that event using
        instance #2
        """
        event = create_chat_event(ChatMessageEvent)
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
            await self.event_broker.post_event(channel=channel, event=event)

            # Check that get_events() returns posted event for user_1 (instance #1 of
            # EventBroker) and user_2 (instance #2 of EventBroker)
            events_res_1 = await self.event_broker.get_events(user_id_1)
            assert len(events_res_1) == 1
            assert events_res_1[0].model_dump_json() == event.model_dump_json()
            events_res_2 = await self.event_broker_instance_2.get_events(user_id_2)
            assert len(events_res_2) == 1
            assert events_res_2[0].model_dump_json() == event.model_dump_json()

    async def test_ack_events__dont_ack__subsequent_calls_return_empty(self):
        """
        Post event and receive it without acknowledgement.
        Second call of get_events() returns empty list.
        Post one more event.
        Third call of get_events() returns empty list.
        """
        event = create_chat_event(ChatMessageEvent)
        event_2 = create_chat_event(ChatMessageEvent)
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user_1 to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event to the channel
            await self._post_message(
                routing_key=channel, message=event.model_dump_json()
            )

            # Check that get_events() returns posted event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 1
            assert events_res[0].model_dump_json() == event.model_dump_json()

            # Check that second call of get_events() returns empty list
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 0

            # Post one more event to the channel
            await self._post_message(
                routing_key=channel, message=event_2.model_dump_json()
            )

            # Check that third call of get_events() returns empty list
            # (because first call wasn't acknowledged)
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 0

    async def test_ack_events__dont_ack__subsequent_call_after_timeout_return_all(self):
        """
        Post event and receive it without acknowledgement.
        Post one more event.
        Wait 3s (ack timeout).
        Second call of get_events() returns first event again.
        """
        event = create_chat_event(ChatMessageEvent)
        event_2 = create_chat_event(ChatMessageEvent)
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user_1 to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event to the channel
            await self._post_message(
                routing_key=channel, message=event.model_dump_json()
            )

            # Check that get_events() returns posted event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 1
            assert events_res[0].model_dump_json() == event.model_dump_json()

            # Post one more event to the channel
            await self._post_message(
                routing_key=channel, message=event_2.model_dump_json()
            )

            # Wait 3 sec
            with freeze_time(datetime.now() + timedelta(seconds=3)):
                # Check that second call of get_events() returns first event again
                # (because ack timeout riched and broker sends it again)
                events_res = await self.event_broker.get_events(user_id)
                assert len(events_res) == 1
                assert events_res[0].model_dump_json() == event.model_dump_json()

    async def test_ack_events__dont_ack__subsequent_call_after_2nd_timeout_return_all(
        self,
    ):
        """
        Post event and receive it without acknowledgement.
        Post one more event.
        Wait 3s (ack timeout).
        Second call of get_events() returns first event again.
        Third call of get_events() returns empty list.
        Wait another 3s (ack timeout).
        Forth call of get_events() returns first event again.
        """
        event = create_chat_event(ChatMessageEvent)
        event_2 = create_chat_event(ChatMessageEvent)
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user_1 to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event to the channel
            await self._post_message(
                routing_key=channel, message=event.model_dump_json()
            )

            # Check that get_events() returns posted event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 1
            assert events_res[0].model_dump_json() == event.model_dump_json()

            # Post one more event to the channel
            await self._post_message(
                routing_key=channel, message=event_2.model_dump_json()
            )

            # Wait 3 sec
            with freeze_time(datetime.now() + timedelta(seconds=3)):
                # Check that second call of get_events() returns first event again
                # (because ack timeout riched and broker sends it again)
                events_res = await self.event_broker.get_events(user_id)
                assert len(events_res) == 1
                assert events_res[0].model_dump_json() == event.model_dump_json()

                # Third call or get_events() returns empty list
                events_res = await self.event_broker.get_events(user_id)
                assert len(events_res) == 0

                # Wait another 3 sec
                with freeze_time(datetime.now() + timedelta(seconds=3)):
                    # Check that forth call of get_events() returns first event again
                    # (because ack timeout riched and broker sends it again)
                    events_res = await self.event_broker.get_events(user_id)
                    assert len(events_res) == 1
                    assert events_res[0].model_dump_json() == event.model_dump_json()

    async def test_ack_events__returns_next_events_after_acknowledgement(self):
        """
        Post event and receive it.
        Post one more event.
        Second call of get_events() returns empty list.
        Acknowlege.
        Third call of get_events() returns second event.
        """
        event_1 = create_chat_event(ChatMessageEvent)
        event_2 = create_chat_event(ChatMessageEvent)
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user_1 to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event_1 to the channel
            await self._post_message(
                routing_key=channel, message=event_1.model_dump_json()
            )

            # Check that get_events() returns posted event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 1
            assert events_res[0].model_dump_json() == event_1.model_dump_json()

            # Post event_2 to the channel
            await self._post_message(
                routing_key=channel, message=event_2.model_dump_json()
            )

            # Check that second call of get_events() returns empty list
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 0

            # Acknowledge receiving event_1
            await self.event_broker.acknowledge_events(user_id=user_id)

            # Check that third call of get_events() returns event_2
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 1
            assert events_res[0].model_dump_json() == event_2.model_dump_json()

    async def test_ack_events__returns_list_of_events_that_were_acknoledged(self):
        """
        Post event and receive it.
        Post one more event.
        Acknowlege. acknowledge_events() returns list of events, returned by the first
        call of get_events.
        """
        events = [create_chat_event(ChatMessageEvent) for _ in range(3)]
        event_next = create_chat_event(ChatMessageEvent)
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user_1 to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post events to the channel
            for event in events:
                await self._post_message(
                    routing_key=channel, message=event.model_dump_json()
                )

            # Check that get_events() returns posted events
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == len(events)
            assert [ev.model_dump_json() for ev in events_res] == [
                ev.model_dump_json() for ev in events
            ]

            # Post event_next to the channel
            await self._post_message(
                routing_key=channel, message=event_next.model_dump_json()
            )

            # Check that second call of get_events() returns empty list
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 0

            # Acknowledge receiving events
            events_cknowledged = await self.event_broker.acknowledge_events(
                user_id=user_id
            )

            # Chack that the list of acknowledged events equals to list of first events
            # (without event_next)
            assert len(events_cknowledged) == len(events)
            assert [ev.model_dump_json() for ev in events_cknowledged] == [
                ev.model_dump_json() for ev in events
            ]

    async def test_unacknowledged__clear_on_context_exit(self):
        """
        Post event and receive it without acknowledgement.
        Exit context manager and enter again.
        Post one more event.
        Second call of get_events() returns empty second event.
        """
        event_1 = create_chat_event(ChatMessageEvent)
        event_2 = create_chat_event(ChatMessageEvent)
        user_id = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id):
            # Subscribe user_1 to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event_1 to the channel
            await self._post_message(
                routing_key=channel, message=event_1.model_dump_json()
            )

            # Check that get_events() returns posted event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 1
            assert events_res[0].model_dump_json() == event_1.model_dump_json()

        async with self.event_broker.session(user_id):
            # Subscribe user_1 to the channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id)

            # Post event_2 to the channel
            await self._post_message(
                routing_key=channel, message=event_2.model_dump_json()
            )

            # Check that second call of get_events() returns second event
            events_res = await self.event_broker.get_events(user_id)
            assert len(events_res) == 1
            assert events_res[0].model_dump_json() == event_2.model_dump_json()

    # Error handling

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_get_events__failure_on_get_events_str_exception(
        self, exception_raise: Exception
    ):
        """
        get_events() raises EventBrokerFail on any error in _get_events_str()
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            with patch.object(
                self.event_broker.__class__,
                "_get_events_str",
                new=Mock(side_effect=exception_raise),
            ):
                with pytest.raises(EventBrokerFail):
                    await self.event_broker.get_events(user_id_1)

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_get_events__failure_on_other_exceptions(
        self, exception_raise: Exception
    ):
        """
        get_events() raises EventBrokerFail on any error outside in _get_events_str()
        """
        user_id_1 = uuid.uuid4()

        async with self._brake_event_broker(exception_raise):
            with pytest.raises(EventBrokerFail):
                await self.event_broker.get_events(user_id_1)

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_post_event__failure_on_post_event_str_exception(
        self, exception_raise: Exception
    ):
        """
        post_event() raises EventBrokerFail on any error in _post_event_str()
        """
        user_id_1 = uuid.uuid4()
        channel = channel_code("chat", uuid.uuid4())
        event = create_chat_event(ChatMessageEvent)

        async with self.event_broker.session(user_id_1):
            # Subcribe user_1 to channel
            await self.event_broker.subscribe(channel=channel, user_id=user_id_1)

            with patch.object(
                self.event_broker.__class__,
                "_post_event_str",
                new=Mock(side_effect=exception_raise),
            ):
                with pytest.raises(EventBrokerFail):
                    await self.event_broker.post_event(channel=channel, event=event)

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_post_event__failure_on_other_exceptions(
        self, exception_raise: Exception
    ):
        """
        post_event() raises EventBrokerFail on any error outside _post_event_str()
        """
        channel = channel_code("chat", uuid.uuid4())
        event = create_chat_event(ChatMessageEvent)

        async with self._brake_event_broker(exception_raise):
            with pytest.raises(EventBrokerFail):
                await self.event_broker.post_event(channel=channel, event=event)

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_session__failure(self, exception_raise: Exception):
        """
        session() raises EventBrokerFail on any error in _session()
        """
        user_id_1 = uuid.uuid4()
        with patch.object(
            self.event_broker.__class__,
            "_session",
            new=Mock(side_effect=exception_raise),
        ):
            with pytest.raises(EventBrokerFail):
                async with self.event_broker.session(user_id_1):
                    pass

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_subscribe__failure(self, exception_raise: Exception):
        """
        subscribe() raises EventBrokerFail on any error in it
        """
        user_id_1 = uuid.uuid4()

        # Brake event_broker so that it will always raise errors
        async with self._brake_event_broker(exception_raise):
            with pytest.raises(EventBrokerFail):
                await self.event_broker.subscribe("channel_1", user_id_1)

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_subscribe_list__failure(self, exception_raise: Exception):
        """
        subscribe_list() raises EventBrokerFail on any error in it
        """
        user_id_1 = uuid.uuid4()

        # Brake event_broker so that it will always raise errors
        async with self._brake_event_broker(exception_raise):
            with pytest.raises(EventBrokerFail):
                await self.event_broker.subscribe_list(
                    ["channel_1", "channel_2"], user_id_1
                )

    @pytest.mark.parametrize(
        "exception_raise",
        (Exception(), EventBrokerFail("-"), EventBrokerException("-")),
    )
    async def test_acknowledge_events__failure(self, exception_raise: Exception):
        """
        acknowledge_events() raises EventBrokerFail on any error in it
        """
        user_id_1 = uuid.uuid4()

        # Brake event_broker so that it will always raise errors
        async with self._brake_event_broker(exception_raise):
            with pytest.raises(EventBrokerFail):
                await self.event_broker.acknowledge_events(user_id_1)

    # Utils

    @asynccontextmanager
    async def _brake_event_broker(self, exception: Exception):
        self.event_broker._unacknowledged_events = Mock(side_effect=exception)
        async with self._brake_event_broker_derrived(exception):
            yield

    # Methods below should be implemented in the descendant class

    async def _post_message(self, routing_key: str, message: str):
        raise NotImplementedError

    @asynccontextmanager
    async def _brake_event_broker_derrived(self, exception: Exception):
        raise NotImplementedError
        yield
