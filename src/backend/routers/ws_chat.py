from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket

from backend.dependencies import chat_manager_dep
from backend.services.chat_manager.chat_manager import ChatManager

ws_chat_router = APIRouter(prefix="/ws", tags=["websocket"])


@ws_chat_router.websocket("/chat")
async def ws_chat(
    websocket: WebSocket,
    chat_manager: Annotated[ChatManager, Depends(chat_manager_dep)],
):
    await websocket.accept()
    while True:
        await websocket.send_text("Hello, world!")
        await websocket.receive_text()
