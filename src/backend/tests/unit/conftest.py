from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.dependencies import event_broker_dep, sqla_sessionmaker_dep
from backend.main import app
from backend.models.base import BaseModel
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
def chat_manager(async_session_maker: async_sessionmaker):
    chat_manager = ChatManager(
        uow=SQLAlchemyUnitOfWork(async_session_maker),
        event_broker=InMemoryEventBroker(),
    )
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

    def get_event_broker():
        return event_broker

    app.dependency_overrides[sqla_sessionmaker_dep] = get_sessionmaker
    app.dependency_overrides[event_broker_dep] = get_event_broker
    client = TestClient(app)

    yield client

    app.dependency_overrides.pop(sqla_sessionmaker_dep)
    app.dependency_overrides.pop(event_broker_dep)
