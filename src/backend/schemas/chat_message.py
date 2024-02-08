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


class ChatMessagePersistedSchema(BaseSchema):
    id: int
    dt: datetime


ChatMessageAny: TypeAlias = Union["ChatUserMessageSchema", "ChatNotificationSchema"]
AnnotatedChatMessageAny: TypeAlias = Annotated[
    ChatMessageAny, Field(discriminator="is_notification")
]


# User message


class ChatUserMessageCreateSchema(ChatMessageSchemaBase):
    """
    User message before being saved in the DB
    """

    is_notification: Literal[False] = Field(default=False)
    sender_id: uuid.UUID


class ChatUserMessageSchema(ChatUserMessageCreateSchema, ChatMessagePersistedSchema):
    """
    User message that has been saved in the DB (has `id` and `dt`)
    """

    pass


# Notification


class ChatNotificationCreateSchema(ChatMessageSchemaBase):
    """
    Notification before being saved in the DB
    """

    is_notification: Literal[True] = Field(default=True)
    params: str


class ChatNotificationSchema(ChatNotificationCreateSchema, ChatMessagePersistedSchema):
    """
    Notification that has been saved in the DB (has `id` and `dt`)
    """

    pass
