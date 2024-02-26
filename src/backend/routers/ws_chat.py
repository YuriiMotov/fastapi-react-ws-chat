import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from backend.dependencies import chat_manager_dep, get_current_user
from backend.schemas.client_packet import ClientPacket
from backend.services import chat_server
from backend.services.chat_manager.chat_manager import ChatManager

ws_chat_router = APIRouter(prefix="/ws", tags=["websocket"])


@ws_chat_router.websocket("/chat")
async def ws_chat(
    websocket: WebSocket,
    chat_manager: Annotated[ChatManager, Depends(chat_manager_dep)],
    current_user_id: Annotated[uuid.UUID, Depends(get_current_user)],
):
    await websocket.accept()
    await chat_manager.subscribe_for_updates(current_user_id=current_user_id)
    try:
        while True:
            # Receive packet from websocket and process it
            try:
                client_packet_str = await asyncio.wait_for(
                    websocket.receive_text(), timeout=0.1
                )
            except TimeoutError:  # Nothing to recieive
                pass
            else:
                client_packet = ClientPacket.model_validate_json(client_packet_str)
                server_resp = await chat_server.process_client_request_packet(
                    chat_manager=chat_manager,
                    packet=client_packet,
                    current_user_id=current_user_id,
                )
                await websocket.send_text(server_resp.model_dump_json())
            # Check for new events and send via websocket

    except WebSocketDisconnect:
        await chat_manager.unsubscribe_from_updates(current_user_id=current_user_id)
