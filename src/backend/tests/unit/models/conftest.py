from typing import AsyncGenerator
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)

from models.base import BaseModel


@pytest.fixture(scope="session")
def engine() -> AsyncEngine:
    yield create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}
    )


@pytest.fixture()
async def prepare_database(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


@pytest.fixture(scope="session")
def async_session_maker(engine) -> async_sessionmaker:
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture()
async def async_session(
    prepare_database, async_session_maker: async_sessionmaker
) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
