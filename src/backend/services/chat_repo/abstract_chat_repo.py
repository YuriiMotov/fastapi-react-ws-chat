from abc import ABC, abstractmethod
import uuid
from schemas.chat import ChatSchema

from models.chat_message import ChatUserMessage, ChatNotification
from schemas.chat_message import (
    ChatUserMessageCreateSchema,
    ChatNotificationCreateSchema,
)

PAGE_LIMIT_DEFAULT = 20


class ChatRepoException(Exception):
    pass


class AbstractChatRepo(ABC):

    @abstractmethod
    async def add_chat(self, chat: ChatSchema) -> ChatSchema:
        raise NotImplementedError()

    @abstractmethod
    async def get_chats(
        self, owner_id: uuid.UUID, offset: int = 0, limit: int = PAGE_LIMIT_DEFAULT
    ) -> list[ChatSchema]:
        raise NotImplementedError()

    @abstractmethod
    async def add_user_to_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def add_message(
        self, message: ChatUserMessageCreateSchema
    ) -> ChatUserMessage:
        raise NotImplementedError()

    @abstractmethod
    async def add_notification(
        self, notification: ChatNotificationCreateSchema
    ) -> ChatNotification:
        raise NotImplementedError()
