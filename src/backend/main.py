from fastapi import FastAPI

from backend.routers.ws_chat import ws_chat_router

app = FastAPI(title="FastAPI websocket chat", version="0.0.1")

app.include_router(ws_chat_router)
