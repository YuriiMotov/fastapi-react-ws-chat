import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.database import engine
from backend.dependencies import sqla_sessionmaker_dep
from backend.models.base import BaseModel
from backend.models.chat import Chat
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.routers.ws_chat import ws_chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Create DB tables and fill by test data
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    sessionmaker = sqla_sessionmaker_dep()
    async with sessionmaker() as session:
        user = User(id=uuid.UUID("ef376e46-db3b-4beb-8170-82940d849847"), name="I")
        chats = [
            Chat(id=uuid.uuid4(), title=f"Chat {i}", owner_id=user.id) for i in range(3)
        ]
        user_chat_links = [
            UserChatLink(user_id=user.id, chat_id=chat.id) for chat in chats
        ]
        session.add_all((user, *chats, *user_chat_links))
        await session.commit()

    yield


app = FastAPI(title="FastAPI websocket chat", version="0.0.1", lifespan=lifespan)


app.include_router(ws_chat_router)
