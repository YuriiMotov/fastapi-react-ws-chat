import uuid
from typing import Literal, TypeAlias, Union

from pydantic import Field

from backend.schemas.chat import ChatCreateSchema
from backend.schemas.chat_message import ChatUserMessageCreateSchema

from .base import BaseSchema

ClientPacketData: TypeAlias = Union[
    "CMDGetJoinedChats",
    "CMDAddUserToChat",
    "CMDSendMessage",
    "CMDGetMessages",
    "CMDEditMessage",
    "CMDAcknowledgeEvents",
    "CMDGetFirstCircleListUpdates",
    "CMDGetUserAutocomplete",
    "CMDCreateChat",
]


class ClientPacket(BaseSchema):
    """
    Container for client's command or request
    (client is sender)
    """

    id: int
    data: ClientPacketData = Field(discriminator="packet_type")


class CMDGetJoinedChats(BaseSchema):
    packet_type: Literal["CMDGetJoinedChats"] = "CMDGetJoinedChats"


class CMDAddUserToChat(BaseSchema):
    packet_type: Literal["CMDAddUserToChat"] = "CMDAddUserToChat"
    chat_id: uuid.UUID
    user_id: uuid.UUID


class CMDSendMessage(BaseSchema):
    packet_type: Literal["CMDSendMessage"] = "CMDSendMessage"
    message: ChatUserMessageCreateSchema


class CMDGetMessages(BaseSchema):
    packet_type: Literal["CMDGetMessages"] = "CMDGetMessages"
    chat_id: uuid.UUID
    start_id: int | None = None
    order_desc: bool | None = None
    limit: int | None = None


class CMDEditMessage(BaseSchema):
    packet_type: Literal["CMDEditMessage"] = "CMDEditMessage"
    message_id: int
    text: str


class CMDAcknowledgeEvents(BaseSchema):
    packet_type: Literal["CMDAcknowledgeEvents"] = "CMDAcknowledgeEvents"


class CMDGetUserAutocomplete(BaseSchema):
    packet_type: Literal["CMDGetUserAutocomplete"] = "CMDGetUserAutocomplete"
    name_filter: str
    limit: int | None = None
    offset: int | None = None


class CMDGetFirstCircleListUpdates(BaseSchema):
    packet_type: Literal["CMDGetFirstCircleListUpdates"] = (
        "CMDGetFirstCircleListUpdates"
    )


class CMDCreateChat(BaseSchema):
    packet_type: Literal["CMDCreateChat"] = "CMDCreateChat"
    chat_data: ChatCreateSchema
