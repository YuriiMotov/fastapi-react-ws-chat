import uuid
from typing import cast

import pytest
from sqlalchemy import insert, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.tests.unit.chat_repo.chat_repo_test_base import ChatRepoTestBase


class TestChatRepoMemory(ChatRepoTestBase):
    """
    Test class for SQLAlchemyChatRepo
    (concrete implementation of AbstractChatRepo interface).

    Test methods are implemented in the base test class (ChatRepoTestBase).
    """

    @pytest.fixture(autouse=True)
    def _create_repo(self, async_session: AsyncSession):
        self._session = async_session
        self.repo = SQLAlchemyChatRepo(async_session)
        yield

    async def _check_if_chat_has_persisted(self, chat_id: uuid.UUID) -> bool:
        chat = await self._session.get(Chat, chat_id)
        return chat is not None

    async def _check_if_message_has_persisted(self, message_id: int) -> bool:
        message = await self._session.get(ChatMessage, message_id)
        return message is not None

    async def _check_if_user_chat_link_has_persisted(
        self, user_id: uuid.UUID, chat_id: uuid.UUID
    ) -> bool:
        user_chat_link = await self._session.scalar(
            select(UserChatLink)
            .where(UserChatLink.chat_id == chat_id)
            .where(UserChatLink.user_id == user_id)
        )
        return user_chat_link is not None

    async def _create_user(self, user_id: uuid.UUID, name: str = "user") -> User:
        user = await self._session.scalar(
            insert(User).returning(User),
            {"id": user_id, "name": name},
        )
        if user is None:
            raise Exception()
        return user

    async def _break_connection(self):
        async def raise_error(*args, **kwargs):
            raise OperationalError("", "", Exception())

        sqla_repo = cast(SQLAlchemyChatRepo, self.repo)
        sqla_repo._session.execute = raise_error  # type: ignore
        sqla_repo._session.scalar = raise_error  # type: ignore
        sqla_repo._session.scalars = raise_error  # type: ignore
        sqla_repo._session.get = raise_error  # type: ignore
