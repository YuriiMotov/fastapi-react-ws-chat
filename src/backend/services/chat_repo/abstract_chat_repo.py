from abc import ABC, abstractmethod
import uuid
from schemas.chat import ChatSchema

from schemas.chat_message import (
    ChatNotificationSchema,
    ChatUserMessageCreateSchema,
    ChatNotificationCreateSchema,
    ChatUserMessageSchema,
)


class AbstractChatRepo(ABC):

    @abstractmethod
    async def add_chat(self, chat: ChatSchema) -> ChatSchema:
        """
        Add chat record to the DB.

        Raises:
         - ChatRepoRequestError (duplicated chat id, wrong owner id)
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_owned_chats(
        self, owner_id: uuid.UUID, offset: int = 0, limit: int | None = None
    ) -> list[ChatSchema]:
        """
        Get chat list by owner id.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_joined_chat_ids(
        self, user_id: uuid.UUID, offset: int = 0, limit: int | None = None
    ) -> list[uuid.UUID]:
        """
        Get chat list by user id.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def add_user_to_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Add user-chat link record to the DB.

        Raises:
         - ChatRepoRequestError (wrong chat id, user-chat link already exists)
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def add_message(
        self, message: ChatUserMessageCreateSchema
    ) -> ChatUserMessageSchema:
        """
        Add message record to the DB.

        Raises:
         - ChatRepoRequestError (wrong chat id, wrong sender id)
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def add_notification(
        self, notification: ChatNotificationCreateSchema
    ) -> ChatNotificationSchema:
        """
        Add notification record to the DB.

        Raises:
         - ChatRepoRequestError (wrong chat id)
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()
