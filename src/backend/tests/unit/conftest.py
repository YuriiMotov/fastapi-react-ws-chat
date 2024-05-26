import uuid
from typing import Annotated, AsyncGenerator, Generator

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.auth_setups import Scopes, pwd_context
from backend.dependencies import (
    event_broker_dep,
    get_current_user,
    sqla_sessionmaker_dep,
)
from backend.main import app
from backend.models.base import BaseModel
from backend.models.user import User
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker
from backend.services.uow.sqla_uow import SQLAlchemyUnitOfWork


@pytest.fixture(scope="session")
def engine() -> Generator[AsyncEngine, None, None]:
    yield create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}
    )


@pytest.fixture()
async def prepare_database(engine):
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


@pytest.fixture()
def async_session_maker(
    engine, prepare_database
) -> Generator[async_sessionmaker, None, None]:
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture()
async def async_session(
    async_session_maker: async_sessionmaker,
) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


@pytest.fixture()
def event_broker_user_id_list() -> list[uuid.UUID]:
    return [uuid.uuid4() for _ in range(3)]


@pytest.fixture()
async def chat_manager(
    async_session_maker: async_sessionmaker, event_broker_user_id_list: list[uuid.UUID]
):
    event_broker = InMemoryEventBroker()
    chat_manager = ChatManager(
        uow=SQLAlchemyUnitOfWork(async_session_maker),
        event_broker=event_broker,
    )
    async with (
        event_broker.session(event_broker_user_id_list[0]),
        event_broker.session(event_broker_user_id_list[1]),
        event_broker.session(event_broker_user_id_list[2]),
    ):
        yield chat_manager


@pytest.fixture()
def event_broker():
    return InMemoryEventBroker()


@pytest.fixture(name="client")
def get_test_client(
    async_session_maker: async_sessionmaker, event_broker: InMemoryEventBroker
):
    def get_sessionmaker():
        return async_session_maker

    async def get_event_broker(
        current_user_id: Annotated[uuid.UUID, Depends(get_current_user)]
    ):
        async with event_broker.session(current_user_id):
            yield event_broker

    app.dependency_overrides[sqla_sessionmaker_dep] = get_sessionmaker
    app.dependency_overrides[event_broker_dep] = get_event_broker
    client = TestClient(app)
    yield client

    app.dependency_overrides.pop(sqla_sessionmaker_dep)
    app.dependency_overrides.pop(event_broker_dep)


@pytest.fixture()
async def registered_user_data(async_session: AsyncSession):
    password = str(uuid.uuid4())
    user_data = {
        "id": uuid.uuid4().hex,
        "name": f"User_{uuid.uuid4()}",
        "password": password,
        "scope": " ".join([e.value for e in Scopes]),
    }
    hashed_password = pwd_context.hash(password)
    user = User(
        id=uuid.UUID(user_data["id"]),
        name=user_data["name"],
        hashed_password=hashed_password,
        scope=user_data["scope"],
    )
    async_session.add(user)
    await async_session.commit()
    yield user_data
