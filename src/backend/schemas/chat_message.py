import json
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, TypeAlias, Union

from pydantic import Field, field_serializer, field_validator

from .base import BaseSchema

# Common base to User message and Notification


class ChatMessageSchemaBase(BaseSchema):
    chat_id: uuid.UUID
    text: str
    is_notification: bool


class ChatMessagePersistedSchema(BaseSchema):
    id: int
    dt: datetime


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
    params: dict[str, str]

    @field_validator("params", mode="before")
    @classmethod
    def decode_params(cls, v: Any):
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("params is not valid JSON-strings")
        return v

    @field_serializer("params", when_used="always")
    def serialize_params(self, params: dict[str, str]):
        return json.dumps(params)


class ChatNotificationSchema(ChatNotificationCreateSchema, ChatMessagePersistedSchema):
    """
    Notification that has been saved in the DB (has `id` and `dt`)
    """

    pass


# Discriminated union type

ChatMessageAny: TypeAlias = Union[ChatUserMessageSchema, ChatNotificationSchema]
AnnotatedChatMessageAny: TypeAlias = Annotated[
    ChatMessageAny, Field(discriminator="is_notification")
]
