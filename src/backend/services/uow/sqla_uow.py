from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.services.chat_repo.chat_repo_exc import ChatRepoDatabaseError
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.uow.abstract_uow import (
    USE_AS_CONTEXT_MANAGER_ERROR,
    AbstractUnitOfWork,
)
from backend.services.uow.uow_exc import UnitOfWorkException


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    _session: AsyncSession | None

    def __init__(self, session_maker: async_sessionmaker):
        self._session_factory = session_maker

    async def __aenter__(self):
        session = self._session_factory()
        self._session = session
        self.chat_repo = SQLAlchemyChatRepo(session)

    async def __aexit__(self, *args):
        if self._session is not None:
            try:
                await self.rollback()
                await self._session.close()
                self._session = None
            except SQLAlchemyError as e:
                raise ChatRepoDatabaseError(detail=str(e))
            except Exception as e:
                raise UnitOfWorkException(detail=str(e))

    async def commit(self):
        if self._session is None:
            raise UnitOfWorkException(detail=USE_AS_CONTEXT_MANAGER_ERROR)
        try:
            await self._session.commit()
        except SQLAlchemyError as e:
            raise ChatRepoDatabaseError(detail=str(e))
        except Exception as e:
            raise UnitOfWorkException(detail=str(e))

    async def rollback(self):
        if self._session is None:
            raise UnitOfWorkException(detail=USE_AS_CONTEXT_MANAGER_ERROR)
        try:
            await self._session.rollback()
        except SQLAlchemyError as e:
            raise ChatRepoDatabaseError(detail=str(e))
        except Exception as e:
            raise UnitOfWorkException(detail=str(e))
