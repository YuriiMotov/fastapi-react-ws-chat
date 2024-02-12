from typing import cast
import uuid

import pytest
from services.uow.abstract_uow import UnitOfWorkException
from models.chat import Chat
from services.uow.sqla_uow import SQLAlchemyUnitOfWork
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession


class TestSQLAlchemyUOW:
    uow: SQLAlchemyUnitOfWork

    @pytest.fixture(autouse=True)
    def _create_uow(self, async_session_maker: async_sessionmaker):
        self._session_maker = async_session_maker
        self.uow = SQLAlchemyUnitOfWork(async_session_maker)
        yield

    async def test_commit(self):
        async with self.uow:
            chat = Chat(id=uuid.uuid4(), title="", owner_id=uuid.uuid4())
            cast(AsyncSession, self.uow._session).add(chat)
            await self.uow.commit()

        async with self.uow:
            chat_from_db = await cast(AsyncSession, self.uow._session).get(
                Chat, chat.id
            )
            assert chat_from_db is not None

    async def test_rollback(self):
        async with self.uow:
            chat = Chat(id=uuid.uuid4(), title="", owner_id=uuid.uuid4())
            cast(AsyncSession, self.uow._session).add(chat)
            # Do not call `self.uow.commit()`

        async with self.uow:
            chat_from_db = await cast(AsyncSession, self.uow._session).get(
                Chat, chat.id
            )
            assert chat_from_db is None

    async def test_session_close_on_exit(self):
        async with self.uow:
            pass
        with pytest.raises(UnitOfWorkException):
            await self.uow.commit()
