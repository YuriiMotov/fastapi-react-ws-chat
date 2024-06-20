from typing import Literal, TypeAlias, Union

from pydantic import Field

from backend.schemas.chat import ChatExtSchema
from backend.schemas.chat_message import ChatMessageAny
from backend.schemas.event import AnyEventDiscr
from backend.schemas.user import UserSchema
from backend.services.chat_manager.chat_manager_exc import ChatManagerException

from .base import BaseSchema

ServerPacketData: TypeAlias = Union[
    "SrvRespError",
    "SrvRespSucessNoBody",
    "SrvRespGetJoinedChatList",
    "SrvRespGetMessages",
    "SrvEventList",
    "SrvRespGetUserList",
]


class ServerPacket(BaseSchema):
    """
    Container for server's response or notification
    (server is sender)
    """

    request_packet_id: int | None
    data: ServerPacketData = Field(discriminator="packet_type")


# Responses


class SrvRespError(BaseSchema):
    """
    Unseccessful response (error)
    """

    packet_type: Literal["RespError"] = "RespError"
    success: Literal[False] = False
    error_data: ChatManagerException


class SrvRespSuccess(BaseSchema):
    """
    Common base for all successful responses
    """

    success: Literal[True] = True


class SrvRespSucessNoBody(SrvRespSuccess):
    """
    Schema for all successful responses without body (there is no need to send any data)
    """

    packet_type: Literal["RespSuccessNoBody"] = "RespSuccessNoBody"


class SrvRespGetJoinedChatList(SrvRespSuccess):
    """
    Response for CMDGetChats command.
    Contains list of user's chats
    """

    packet_type: Literal["RespGetJoinedChatList"] = "RespGetJoinedChatList"
    chats: list[ChatExtSchema]


class SrvRespGetMessages(SrvRespSuccess):
    """
    Response for CMDGetMessages command.

    Contains list of messages according to the request.
    """

    packet_type: Literal["RespGetMessages"] = "RespGetMessages"
    messages: list[ChatMessageAny]


class SrvRespGetUserList(SrvRespSuccess):
    """
    Response for CMDGetUserList command.
    Contains list of users by filter
    """

    packet_type: Literal["SrvRespGetUserList"] = "SrvRespGetUserList"
    users: list[UserSchema]


# Events


class SrvEventList(BaseSchema):
    packet_type: Literal["SrvEventList"] = "SrvEventList"
    events: list[AnyEventDiscr]
