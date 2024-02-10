from collections import defaultdict, deque
import uuid

from services.message_broker.abstract_message_broker import (
    AbstractMessageBroker,
    UserNotSubscribed,
)

MAX_DEQUE_SIZE = 1000


class InMemoryMessageBroker(AbstractMessageBroker):

    def __init__(self, max_deque_size: int = MAX_DEQUE_SIZE):
        self._max_deque_size = max_deque_size
        self._subscribers: set[str] = set()
        self._subscribtions: defaultdict[str, set[str]] = defaultdict(set)
        self._message_queue: defaultdict[str, deque[str]] = defaultdict(deque)

    async def subscribe(self, channel: str, user_id: uuid.UUID):
        """
        Subscribe user to all new messages in specific channel.
        """
        user_id_str = str(user_id)
        channel_subscribers = self._subscribtions[channel]
        channel_subscribers.add(user_id_str)
        self._subscribers.add(user_id_str)

    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        """
        Subscribe user to all new messages in all channels in the list.
        """
        user_id_str = str(user_id)
        for channel in channels:
            self._subscribtions[channel].add(user_id_str)
        self._subscribers.add(user_id_str)

    async def unsubscribe(self, user_id: uuid.UUID):
        """
        Unsubscribe user from all channels.
        """
        user_id_str = str(user_id)
        for channel_subscribers in self._subscribtions.values():
            if user_id_str in channel_subscribers:
                channel_subscribers.remove(user_id_str)
        if user_id_str in self._subscribers:
            self._subscribers.remove(user_id_str)

    async def get_messages(self, user_id: uuid.UUID, limit: int = 20) -> list[str]:
        """
        Return all new messages for specific user.
        """
        user_id_str = str(user_id)
        if user_id_str not in self._subscribers:
            raise UserNotSubscribed()
        messages = self._message_queue[user_id_str]
        return [messages.popleft() for _ in range(min(len(messages), limit))]

    async def post_message(self, channel: str, message: str):
        """
        Post new message to the specific channel.
        """
        channel_subscribers = self._subscribtions[channel]
        for user_id_str in channel_subscribers:
            self._message_queue[user_id_str].append(message)
            if len(self._message_queue[user_id_str]) > self._max_deque_size:
                channel_subscribers.remove(user_id_str)
