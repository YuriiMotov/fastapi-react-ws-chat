import uuid
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models.chat import Chat
from backend.services.uow.sqla_uow import SQLAlchemyUnitOfWork
from backend.services.uow.uow_exc import UnitOfWorkException


class TestSQLAlchemyUOW:
    uow: SQLAlchemyUnitOfWork

    @pytest.fixture(autouse=True)
    def _create_uow(self, async_session_maker: async_sessionmaker):
        self._session_maker = async_session_maker
        self.uow = SQLAlchemyUnitOfWork(async_session_maker)
        yield

    async def test_commit(self, async_session: AsyncSession):
        """
        Calling the commit() method saves changes made with the session
        """
        async with self.uow:
            chat = Chat(id=uuid.uuid4(), title="", owner_id=uuid.uuid4())
            cast(AsyncSession, self.uow._session).add(chat)
            await self.uow.commit()

        chat_from_db = await async_session.get(Chat, chat.id)
        assert chat_from_db is not None

    async def test_rollback(self, async_session: AsyncSession):
        """
        Changes are cancelled if commit() wasn't called
        """
        async with self.uow:
            chat = Chat(id=uuid.uuid4(), title="", owner_id=uuid.uuid4())
            cast(AsyncSession, self.uow._session).add(chat)
            # Do not call `self.uow.commit()`

        chat_from_db = await async_session.get(Chat, chat.id)
        assert chat_from_db is None

    async def test_session_close_on_exit(self):
        """
        UOW's session is no longer active after the exit from the `with` statement
        """
        async with self.uow:
            pass
        with pytest.raises(UnitOfWorkException):
            await self.uow.commit()
