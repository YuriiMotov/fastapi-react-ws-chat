import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import AsyncIterator

from backend.services.event_broker.abstract_event_broker import (
    USE_CONTEXT_ERROR,
    AbstractEventBroker,
)

MAX_DEQUE_SIZE = 1000
ACK_TIMEOUT_SEC = 2


@dataclass
class UnacknowledgedEvents:
    expire_dt: datetime
    sent_events: list[str]


class InMemoryEventBroker(AbstractEventBroker):
    _cls_initialized: bool = False
    _max_deque_size: int
    _subscribers: set[str]
    _subscribtions: defaultdict[str, set[str]]
    _event_queue: dict[str, deque[str]]

    def __init__(self, max_deque_size: int = MAX_DEQUE_SIZE):
        cls = InMemoryEventBroker
        if cls._cls_initialized is False:
            cls._max_deque_size = max_deque_size
            cls._subscribers = set()
            cls._subscribtions = defaultdict(set)
            cls._event_queue = {}
        self._unacknowledged_events: dict[str, UnacknowledgedEvents | None] = (
            defaultdict(None)
        )

    @asynccontextmanager
    async def session(self, user_id: uuid.UUID) -> AsyncIterator[None]:
        cls = InMemoryEventBroker
        user_id_str = str(user_id)
        assert (
            user_id_str not in cls._subscribers
        ), f"session already exists for user {user_id_str}"
        cls._event_queue[user_id_str] = deque()
        cls._subscribers.add(user_id_str)
        self._unacknowledged_events[user_id_str] = None
        yield
        if user_id_str in cls._event_queue:
            cls._event_queue.pop(user_id_str)
        if user_id_str in cls._subscribers:
            cls._subscribers.remove(user_id_str)
        for channel_subscribers in cls._subscribtions.values():
            if user_id_str in channel_subscribers:
                channel_subscribers.remove(user_id_str)
        self._unacknowledged_events[user_id_str] = None

    async def subscribe(self, channel: str, user_id: uuid.UUID):
        cls = InMemoryEventBroker
        user_id_str = str(user_id)
        assert user_id_str in cls._subscribers, USE_CONTEXT_ERROR
        channel_subscribers = cls._subscribtions[channel]
        channel_subscribers.add(user_id_str)

    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        cls = InMemoryEventBroker
        user_id_str = str(user_id)
        assert user_id_str in cls._subscribers, USE_CONTEXT_ERROR
        for channel in channels:
            cls._subscribtions[channel].add(user_id_str)

    async def get_events(
        self, user_id: uuid.UUID, limit: int | None = None
    ) -> list[str]:
        cls = InMemoryEventBroker
        user_id_str = str(user_id)
        assert user_id_str in cls._subscribers, USE_CONTEXT_ERROR
        if unack_data := self._unacknowledged_events[user_id_str]:
            if unack_data.sent_events:
                if unack_data.expire_dt > datetime.now():
                    return []  # Waiting for aknowledgment of previous events
                else:
                    # Ack timeout reached. Send previous events again
                    unack_data.expire_dt = datetime.now() + timedelta(
                        seconds=ACK_TIMEOUT_SEC
                    )
                    return unack_data.sent_events
            self._unacknowledged_events[user_id_str] = None
        events = cls._event_queue[user_id_str]
        if limit is None:
            limit = len(events)
        sent_events = [events.popleft() for _ in range(min(len(events), limit))]
        if sent_events:
            self._unacknowledged_events[user_id_str] = UnacknowledgedEvents(
                expire_dt=(datetime.now() + timedelta(seconds=ACK_TIMEOUT_SEC)),
                sent_events=sent_events,
            )
        return sent_events

    async def acknowledge_events(self, user_id: uuid.UUID):
        user_id_str = str(user_id)
        self._unacknowledged_events[user_id_str] = None

    async def post_event(self, channel: str, event: str):
        cls = InMemoryEventBroker
        channel_subscribers = cls._subscribtions[channel]
        for user_id_str in channel_subscribers:
            cls._event_queue[user_id_str].append(event)
            if len(cls._event_queue[user_id_str]) > cls._max_deque_size:
                channel_subscribers.remove(user_id_str)
