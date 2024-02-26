from typing import Annotated, Literal, Union

from pydantic import Field

from backend.schemas.chat_message import ChatMessageAny

from .base import BaseSchema


class ChatMessageEvent(BaseSchema):
    event_type: Literal["ChatMessageEvent"] = "ChatMessageEvent"
    message: ChatMessageAny = Field(discriminator="is_notification")


# Discriminated union type

AnyEvent = Annotated[Union[ChatMessageEvent,], Field(discriminator="event_type")]
