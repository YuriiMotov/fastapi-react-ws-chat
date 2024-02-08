from copy import deepcopy
import dataclasses
from datetime import datetime
import uuid
from schemas.chat import ChatSchema

from models.chat import Chat
from models.chat_message import ChatMessage, ChatNotification, ChatUserMessage
from schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatNotificationSchema,
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from services.chat_repo.chat_repo_interface import ChatRepo, ChatRepoException


@dataclasses.dataclass
class ChatRepoData:
    chats: dict[str, Chat] = dataclasses.field(default_factory=dict)
    chat_members: dict[str, set[str]] = dataclasses.field(default_factory=dict)
    messages: dict[str, ChatMessage] = dataclasses.field(default_factory=dict)


class ChatRepoMemory(ChatRepo):
    def __init__(self):
        self.data: ChatRepoData = ChatRepoData()
        self._data_next: ChatRepoData = ChatRepoData()
        self._last_messsage_id = 0

    async def commit(self):
        self.data = deepcopy(self._data_next)

    async def rollback(self):
        self._data_next = deepcopy(self.data)

    async def add_chat(self, chat: ChatSchema) -> ChatSchema:
        self._data_next.chats[str(chat.id)] = Chat(**chat.model_dump())
        return chat

    async def add_user_to_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID):
        chat_id_str = str(chat_id)
        chat = self._data_next.chats.get(chat_id_str)
        if chat is None:
            raise ChatRepoException()
        if chat_id_str not in self._data_next.chat_members:
            self._data_next.chat_members[chat_id_str] = []
        self._data_next.chat_members[chat_id_str].add(user_id)

    async def add_message(
        self, message: ChatUserMessageCreateSchema
    ) -> ChatUserMessageSchema:
        chat = self._data_next.chats.get(str(message.chat_id))
        if chat is None:
            raise ChatRepoException()
        self._last_messsage_id += 1
        message_in_db = ChatUserMessage(
            **message.model_dump(exclude_unset=True),
        )
        message_in_db.id = self._last_messsage_id
        message_in_db.dt = datetime.utcnow()

        self._data_next.messages[self._last_messsage_id] = message_in_db
        return ChatUserMessageSchema.model_validate(message_in_db)

    async def add_notification(
        self, notification: ChatNotificationCreateSchema
    ) -> ChatNotificationSchema:
        chat = self._data_next.chats.get(str(notification.chat_id))
        if chat is None:
            raise ChatRepoException()
        self._last_messsage_id += 1
        message_in_db = ChatNotification(
            **notification.model_dump(exclude_unset=True),
        )
        message_in_db.id = self._last_messsage_id
        message_in_db.dt = datetime.utcnow()

        self._data_next.messages[self._last_messsage_id] = message_in_db
        return ChatNotificationSchema.model_validate(message_in_db)
