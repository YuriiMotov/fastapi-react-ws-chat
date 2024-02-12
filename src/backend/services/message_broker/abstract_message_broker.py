from abc import ABC, abstractmethod
import uuid


class MessageBrokerException(Exception):
    pass


class UserNotSubscribed(MessageBrokerException):
    pass


class AbstractMessageBroker(ABC):
    @abstractmethod
    async def subscribe(self, channel: str, user_id: uuid.UUID):
        """
        Subscribe user to all new messages in specific channel.
        """
        raise NotImplementedError()

    @abstractmethod
    async def subscribe_list(self, channels: list[str], user_id: uuid.UUID):
        """
        Subscribe user to all new messages in all channels in the list.
        """
        raise NotImplementedError()

    @abstractmethod
    async def unsubscribe(self, user_id: uuid.UUID):
        """
        Unsubscribe user from all channels.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_messages(self, user_id: uuid.UUID, limit: int = -1) -> list[str]:
        """
        Return all new messages for specific user.
        """
        raise NotImplementedError()

    @abstractmethod
    async def post_message(self, channel: str, message: str):
        """
        Post new message to the specific channel.
        """
        raise NotImplementedError()
