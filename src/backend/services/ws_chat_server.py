import asyncio
import uuid

from fastapi import WebSocket

from backend.schemas.client_packet import (
    ClientPacket,
    CMDAcknowledgeEvents,
    CMDAddUserToChat,
    CMDCreateChat,
    CMDEditMessage,
    CMDGetFirstCircleListUpdates,
    CMDGetJoinedChats,
    CMDGetMessages,
    CMDGetUserList,
    CMDSendMessage,
)
from backend.schemas.server_packet import (
    ServerPacket,
    ServerPacketData,
    SrvEventList,
    SrvRespError,
    SrvRespGetJoinedChatList,
    SrvRespGetMessages,
    SrvRespGetUserList,
    SrvRespSucessNoBody,
)
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import ChatManagerException


async def _process_ws_client_request_packet(
    chat_manager: ChatManager, packet: ClientPacket, current_user_id: uuid.UUID
) -> ServerPacket:

    response_data: ServerPacketData | None = None

    try:
        if isinstance(packet.data, CMDGetJoinedChats):
            chats = await chat_manager.get_joined_chat_list(
                current_user_id=current_user_id
            )
            response_data = SrvRespGetJoinedChatList(chats=chats)
        elif isinstance(packet.data, CMDAddUserToChat):
            await chat_manager.add_user_to_chat(
                current_user_id=current_user_id,
                chat_id=packet.data.chat_id,
                user_id=packet.data.user_id,
            )
            response_data = SrvRespSucessNoBody()
        elif isinstance(packet.data, CMDSendMessage):
            await chat_manager.send_message(
                current_user_id=current_user_id, message=packet.data.message
            )
            response_data = SrvRespSucessNoBody()
        elif isinstance(packet.data, CMDGetMessages):
            messages = await chat_manager.get_message_list(
                **packet.data.model_dump(exclude_none=True, exclude={"packet_type"}),
                current_user_id=current_user_id,
            )
            response_data = SrvRespGetMessages(messages=messages)
        elif isinstance(packet.data, CMDEditMessage):
            await chat_manager.edit_message(
                current_user_id=current_user_id,
                message_id=packet.data.message_id,
                text=packet.data.text,
            )
            response_data = SrvRespSucessNoBody()
        elif isinstance(packet.data, CMDAcknowledgeEvents):
            await chat_manager.acknowledge_events(current_user_id=current_user_id)
            response_data = SrvRespSucessNoBody()
        elif isinstance(packet.data, CMDGetFirstCircleListUpdates):
            await chat_manager.get_first_circle_user_list(
                current_user_id=current_user_id, full=True
            )
            response_data = SrvRespSucessNoBody()
        elif isinstance(packet.data, CMDGetUserList):
            users = await chat_manager.get_user_list(
                **packet.data.model_dump(exclude_none=True, exclude={"packet_type"}),
            )
            response_data = SrvRespGetUserList(users=users)
        elif isinstance(packet.data, CMDCreateChat):
            await chat_manager.create_chat(
                current_user_id=current_user_id, chat_data=packet.data.chat_data
            )
            response_data = SrvRespSucessNoBody()

    except ChatManagerException as exc:
        response_data = SrvRespError(error_data=exc)

    if response_data:
        return ServerPacket(request_packet_id=packet.id, data=response_data)
    else:
        raise Exception()


async def process_ws_client_packets(
    chat_manager: ChatManager, current_user_id: uuid.UUID, websocket: WebSocket
):
    while True:
        try:
            client_packet_str = await asyncio.wait_for(
                websocket.receive_text(), timeout=0.1
            )
        except TimeoutError:  # Nothing to recieive
            break
        else:
            client_packet = ClientPacket.model_validate_json(client_packet_str)
            server_resp = await _process_ws_client_request_packet(
                chat_manager=chat_manager,
                packet=client_packet,
                current_user_id=current_user_id,
            )
            await websocket.send_text(server_resp.model_dump_json())


async def send_events_to_ws_client(
    chat_manager: ChatManager, current_user_id: uuid.UUID, websocket: WebSocket
):
    while True:
        events = await chat_manager.get_events(current_user_id=current_user_id, limit=1)
        if not events:
            break
        srv_packet = ServerPacket(
            request_packet_id=None, data=SrvEventList(events=events)
        )
        await websocket.send_text(srv_packet.model_dump_json())
