import uuid
from abc import ABC, abstractmethod


class AbstractEventBroker(ABC):
    @abstractmethod
    async def subscribe(self, channel: str, user_id: uuid.UUID):
        """
        Subscribe user to all new events in specific channel.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        """
        Subscribe user to all new events in all channels in the list.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def unsubscribe(self, user_id: uuid.UUID):
        """
        Unsubscribe user from all channels.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_events(self, user_id: uuid.UUID, limit: int = -1) -> list[str]:
        """
        Return all new events for specific user.

        Raises:
         - EventBrokerUserNotSubscribedError if user isn't subscribed
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def post_event(self, channel: str, event: str):
        """
        Post new event to the specific channel.

        Raises:
         - EventBrokerFail in case of Event broker failure
        """
        raise NotImplementedError()
