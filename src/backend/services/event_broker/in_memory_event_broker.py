import uuid
from collections import defaultdict, deque

from backend.services.event_broker.abstract_event_broker import AbstractEventBroker
from backend.services.event_broker.event_broker_exc import (
    EventBrokerUserNotSubscribedError,
)

MAX_DEQUE_SIZE = 1000


class InMemoryEventBroker(AbstractEventBroker):
    _max_deque_size: int
    _subscribers: set[str]
    _subscribtions: defaultdict[str, set[str]]
    _event_queue: defaultdict[str, deque[str]]

    def __init__(self, max_deque_size: int = MAX_DEQUE_SIZE):
        cls = InMemoryEventBroker
        cls._max_deque_size = max_deque_size
        cls._subscribers = set()
        cls._subscribtions = defaultdict(set)
        cls._event_queue = defaultdict(deque)

    async def subscribe(self, channel: str, user_id: uuid.UUID):
        cls = InMemoryEventBroker
        user_id_str = str(user_id)
        channel_subscribers = cls._subscribtions[channel]
        channel_subscribers.add(user_id_str)
        cls._subscribers.add(user_id_str)

    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        cls = InMemoryEventBroker

        user_id_str = str(user_id)
        for channel in channels:
            cls._subscribtions[channel].add(user_id_str)
        cls._subscribers.add(user_id_str)

    async def unsubscribe(self, user_id: uuid.UUID):
        cls = InMemoryEventBroker

        user_id_str = str(user_id)
        for channel_subscribers in cls._subscribtions.values():
            if user_id_str in channel_subscribers:
                channel_subscribers.remove(user_id_str)
        if user_id_str in cls._subscribers:
            cls._subscribers.remove(user_id_str)
        if user_id_str in cls._event_queue:
            cls._event_queue.pop(user_id_str)

    async def get_events(self, user_id: uuid.UUID, limit: int = -1) -> list[str]:
        cls = InMemoryEventBroker

        user_id_str = str(user_id)
        if user_id_str not in cls._subscribers:
            raise EventBrokerUserNotSubscribedError()
        events = cls._event_queue[user_id_str]
        if limit == -1:
            limit = len(events)
        return [events.popleft() for _ in range(min(len(events), limit))]

    async def post_event(self, channel: str, user_id: uuid.UUID, event: str):
        cls = InMemoryEventBroker

        channel_subscribers = cls._subscribtions[channel]
        for user_id_str in channel_subscribers:
            cls._event_queue[user_id_str].append(event)
            if len(cls._event_queue[user_id_str]) > cls._max_deque_size:
                channel_subscribers.remove(user_id_str)
