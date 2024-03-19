import uuid
from typing import Annotated, Literal, TypeAlias, Union

from pydantic import Field

from backend.schemas.chat_message import ChatMessageAny

from .base import BaseSchema


class ChatMessageEvent(BaseSchema):
    event_type: Literal["ChatMessageEvent"] = "ChatMessageEvent"
    message: ChatMessageAny = Field(discriminator="is_notification")


class UserAddedToChatNotification(BaseSchema):
    event_type: Literal["UserAddedToChatNotification"] = "UserAddedToChatNotification"
    chat_id: uuid.UUID


# Discriminated union type

AnyEvent: TypeAlias = Union[ChatMessageEvent, UserAddedToChatNotification]

AnyEventDiscr: TypeAlias = Annotated[
    AnyEvent,
    Field(discriminator="event_type"),
]
