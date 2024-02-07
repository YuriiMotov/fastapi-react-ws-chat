import uuid
from datetime import datetime
from typing import Annotated, Literal, TypeAlias, Union

from pydantic import Field

from .base import BaseSchema

# Common base to User message and Notification


class ChatMessageSchemaBase(BaseSchema):
    chat_id: uuid.UUID
    text: str
    is_notification: bool
    dt: datetime


class ChatMessagePersistedSchema(ChatMessageSchemaBase):
    id: int


ChatMessageAny: TypeAlias = Union["ChatUserMessageSchema", "ChatNotificationSchema"]
AnnotatedChatMessageAny: TypeAlias = Annotated[
    ChatMessageAny, Field(discriminator="is_notification")
]


# User message


class ChatUserMessageSchema(ChatMessagePersistedSchema):
    is_notification: Literal[False] = False
    sender_id: uuid.UUID


class ChatUserMessageCreateSchema(ChatMessageSchemaBase):
    is_notification: Literal[False] = Field(exclude=True, default=False)


# Notification


class ChatNotificationSchema(ChatMessagePersistedSchema):
    is_notification: Literal[True] = True
