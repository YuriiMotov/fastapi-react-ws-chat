import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from backend.dependencies import chat_manager_dep, get_current_user
from backend.services import ws_chat_server
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
            await ws_chat_server.process_ws_client_packets(
                chat_manager=chat_manager,
                current_user_id=current_user_id,
                websocket=websocket,
            )

            # Check for new events and send via websocket
            await ws_chat_server.send_events_to_ws_client(
                chat_manager=chat_manager,
                current_user_id=current_user_id,
                websocket=websocket,
            )

    except WebSocketDisconnect:
        await chat_manager.unsubscribe_from_updates(current_user_id=current_user_id)
