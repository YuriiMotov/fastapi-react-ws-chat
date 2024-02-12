from typing import AsyncGenerator, Generator
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from services.chat_manager.chat_manager import ChatManager
from services.message_broker.in_memory_message_broker import InMemoryMessageBroker
from services.uow.sqla_uow import SQLAlchemyUnitOfWork

from models.base import BaseModel


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
        message_broker=InMemoryMessageBroker(),
    )
    yield chat_manager
