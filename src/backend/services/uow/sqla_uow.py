from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.uow.abstract_uow import AbstractUnitOfWork
from backend.services.uow.uow_exc import UnitOfWorkException


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    _session: AsyncSession | None

    def __init__(self, async_session_maker: async_sessionmaker):
        self._session_factory = async_session_maker

    async def __aenter__(self):
        session = self._session_factory()
        self._session = session
        self.chat_repo = SQLAlchemyChatRepo(session)

    async def __aexit__(self, *args):
        if self._session is not None:
            await self.rollback()
            await self._session.close()
            self._session = None

    async def commit(self):
        if self._session is None:
            raise UnitOfWorkException()
        await self._session.commit()

    async def rollback(self):
        if self._session is not None:
            await self._session.rollback()
