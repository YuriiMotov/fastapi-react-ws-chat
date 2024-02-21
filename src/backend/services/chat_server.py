import uuid

from backend.schemas.client_packet import (
    ClientPacket,
    CMDAddUserToChat,
    CMDGetChats,
    CMDGetMessages,
    CMDSendMessage,
)
from backend.schemas.server_packet import (
    ServerPacket,
    ServerPacketData,
    ServerResponseError,
    ServerResponseGetChatList,
    ServerResponseGetMessages,
    ServerResponseSucessNoBody,
)
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import ChatManagerException


async def process_client_request_packet(
    chat_manager: ChatManager, packet: ClientPacket, current_user_id: uuid.UUID
) -> ServerPacket:

    response_data: ServerPacketData | None = None

    try:
        if isinstance(packet.data, CMDGetChats):
            # chats = await chat_manager.get_user_chats()
            chats = []
            response_data = ServerResponseGetChatList(chats=chats)
        elif isinstance(packet.data, CMDAddUserToChat):
            await chat_manager.join_chat(
                current_user_id=current_user_id,
                chat_id=packet.data.chat_id,
                user_id=packet.data.user_id,
            )
            response_data = ServerResponseSucessNoBody()
        elif isinstance(packet.data, CMDSendMessage):
            await chat_manager.send_message(
                current_user_id=current_user_id, message=packet.data.message
            )
            response_data = ServerResponseSucessNoBody()
        elif isinstance(packet.data, CMDGetMessages):
            messages = await chat_manager.get_chat_message_list(
                **packet.data.model_dump(exclude_none=True, exclude={"packet_type"})
            )
            messages_str_encoded = [msg.model_dump_json() for msg in messages]
            response_data = ServerResponseGetMessages(messages=messages_str_encoded)
    except ChatManagerException as exc:
        response_data = ServerResponseError(error_data=exc)

    if response_data:
        return ServerPacket(request_packet_id=packet.id, data=response_data)
    else:
        raise Exception()
