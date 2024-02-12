import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user_chat_link import UserChatLink
from models.chat_message import ChatMessage
from models.chat import Chat

from services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo

from tests.unit.chat_repo.chat_repo_test_base import ChatRepoTestBase


class TestChatRepoMemory(ChatRepoTestBase):

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
