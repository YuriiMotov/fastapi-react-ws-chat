from abc import ABC, abstractmethod
import uuid


class AbstractMessageBroker(ABC):
    @abstractmethod
    async def subscribe(self, channel: str, user_id: uuid.UUID):
        """
        Subscribe user to all new messages in specific channel.

        Raises:
         - MessageBrokerFail in case of Message broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        """
        Subscribe user to all new messages in all channels in the list.

        Raises:
         - MessageBrokerFail in case of Message broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def unsubscribe(self, user_id: uuid.UUID):
        """
        Unsubscribe user from all channels.

        Raises:
         - MessageBrokerFail in case of Message broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_messages(self, user_id: uuid.UUID, limit: int = -1) -> list[str]:
        """
        Return all new messages for specific user.

        Raises:
         - MessageBrokerUserNotSubscribedError if user isn't subscribed
         - MessageBrokerFail in case of Message broker failure
        """
        raise NotImplementedError()

    @abstractmethod
    async def post_message(self, channel: str, message: str):
        """
        Post new message to the specific channel.

        Raises:
         - MessageBrokerFail in case of Message broker failure
        """
        raise NotImplementedError()
