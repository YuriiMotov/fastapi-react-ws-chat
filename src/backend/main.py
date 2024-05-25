import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.auth_setups import pwd_context
from backend.database import engine
from backend.dependencies import sqla_sessionmaker_dep
from backend.models.base import BaseModel
from backend.models.chat import Chat
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.routers.auth import auth_router
from backend.routers.ws_chat import ws_chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Create DB tables and fill by test data
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    sessionmaker = sqla_sessionmaker_dep()
    async with sessionmaker() as session:
        user_1 = User(
            id=uuid.UUID("ef376e46-db3b-4beb-8170-82940d849847"),
            name="John",
            hashed_password=pwd_context.hash("123"),
        )
        user_2 = User(id=uuid.UUID("ef376e56-db3b-4beb-8170-82940d849847"), name="Joe")
        chats = [
            Chat(id=uuid.uuid4(), title=f"Chat {i}", owner_id=user_1.id)
            for i in range(3)
        ]
        chats.append(
            Chat(
                id=uuid.UUID("eccf5b4a-c706-4c05-9ab2-5edc7539daad"),
                title="One more chat",
                owner_id=user_1.id,
            )
        )
        user_chat_links = [
            UserChatLink(user_id=user_1.id, chat_id=chat.id) for chat in chats[:-1]
        ]
        user_chat_links.extend(
            [UserChatLink(user_id=user_2.id, chat_id=chat.id) for chat in chats[:-1]]
        )
        session.add_all((user_1, user_2, *chats, *user_chat_links))
        await session.commit()

    yield


app = FastAPI(title="FastAPI websocket chat", version="0.0.1", lifespan=lifespan)


app.include_router(ws_chat_router)
app.include_router(auth_router)
