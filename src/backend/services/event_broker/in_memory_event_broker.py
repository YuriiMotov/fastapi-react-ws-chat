import uuid
from collections import defaultdict, deque

from backend.services.event_broker.abstract_event_broker import AbstractEventBroker
from backend.services.event_broker.event_broker_exc import (
    EventBrokerUserNotSubscribedError,
)

MAX_DEQUE_SIZE = 1000


class InMemoryEventBroker(AbstractEventBroker):

    def __init__(self, max_deque_size: int = MAX_DEQUE_SIZE):
        self._max_deque_size = max_deque_size
        self._subscribers: set[str] = set()
        self._subscribtions: defaultdict[str, set[str]] = defaultdict(set)
        self._event_queue: defaultdict[str, deque[str]] = defaultdict(deque)

    async def subscribe(self, channel: str, user_id: uuid.UUID):
        user_id_str = str(user_id)
        channel_subscribers = self._subscribtions[channel]
        channel_subscribers.add(user_id_str)
        self._subscribers.add(user_id_str)

    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        user_id_str = str(user_id)
        for channel in channels:
            self._subscribtions[channel].add(user_id_str)
        self._subscribers.add(user_id_str)

    async def unsubscribe(self, user_id: uuid.UUID):
        user_id_str = str(user_id)
        for channel_subscribers in self._subscribtions.values():
            if user_id_str in channel_subscribers:
                channel_subscribers.remove(user_id_str)
        if user_id_str in self._subscribers:
            self._subscribers.remove(user_id_str)
        if user_id_str in self._event_queue:
            self._event_queue.pop(user_id_str)

    async def get_events(self, user_id: uuid.UUID, limit: int = -1) -> list[str]:
        user_id_str = str(user_id)
        if user_id_str not in self._subscribers:
            raise EventBrokerUserNotSubscribedError()
        events = self._event_queue[user_id_str]
        if limit == -1:
            limit = len(events)
        return [events.popleft() for _ in range(min(len(events), limit))]

    async def post_event(self, channel: str, event: str):
        channel_subscribers = self._subscribtions[channel]
        for user_id_str in channel_subscribers:
            self._event_queue[user_id_str].append(event)
            if len(self._event_queue[user_id_str]) > self._max_deque_size:
                channel_subscribers.remove(user_id_str)
