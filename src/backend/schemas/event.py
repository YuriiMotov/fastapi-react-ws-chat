import uuid
from typing import Annotated, Literal, TypeAlias, Union

from pydantic import Field

from backend.schemas.chat import ChatExtSchema
from backend.schemas.chat_message import ChatMessageAny, ChatUserMessageSchema

from .base import BaseSchema


class ChatMessageEvent(BaseSchema):
    event_type: Literal["ChatMessageEvent"] = "ChatMessageEvent"
    message: ChatMessageAny = Field(discriminator="is_notification")


class UserAddedToChatNotification(BaseSchema):
    event_type: Literal["UserAddedToChatNotification"] = "UserAddedToChatNotification"
    chat_id: uuid.UUID


class ChatListUpdate(BaseSchema):
    event_type: Literal["ChatListUpdate"] = "ChatListUpdate"
    action_type: Literal["add", "delete", "update"]
    chat_data: ChatExtSchema


class ChatMessageEdited(BaseSchema):
    event_type: Literal["ChatMessageEdited"] = "ChatMessageEdited"
    message: ChatUserMessageSchema


# Discriminated union type

AnyEvent: TypeAlias = Union[
    ChatMessageEvent, UserAddedToChatNotification, ChatListUpdate, ChatMessageEdited
]

AnyEventDiscr: TypeAlias = Annotated[
    AnyEvent,
    Field(discriminator="event_type"),
]
