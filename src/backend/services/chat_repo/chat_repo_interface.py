from abc import ABC, abstractmethod
import uuid
from schemas.chat import ChatSchema

from models.chat_message import ChatUserMessage, ChatNotification
from schemas.chat_message import (
    ChatUserMessageCreateSchema,
    ChatNotificationCreateSchema,
)


class ChatRepoException(Exception):
    pass


class ChatRepo(ABC):

    @abstractmethod
    async def commit(self):
        raise NotImplementedError()

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError()

    @abstractmethod
    async def add_user_to_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID):
        raise NotImplementedError()

    @abstractmethod
    async def add_chat(self, chat: ChatSchema) -> ChatSchema:
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
