import uuid
from typing import Any
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import RepositoryError
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo


async def test_get_joined_chat_list_success(
    chat_manager: ChatManager, async_session: AsyncSession
):
    """
    get_joined_chat_list() returns list of chats where user is a member
    """
    # Create user, chats and add user to these chats
    user_id = uuid.uuid4()
    async_session.add(User(id=user_id, name="User"))
    chat_owner_id = uuid.uuid4()
    chat_id_list = [uuid.uuid4() for _ in range(3)]
    objects: list[Any] = []
    for chat_id in chat_id_list:
        objects.append(Chat(id=chat_id, title="chat", owner_id=chat_owner_id))
        objects.append(UserChatLink(user_id=user_id, chat_id=chat_id))
    async_session.add_all(objects)
    await async_session.commit()

    # Call chat_manager.get_joined_chat_list() and check results
    chat_list_res = await chat_manager.get_joined_chat_list(current_user_id=user_id)
    assert len(chat_list_res) == len(chat_id_list)
    chat_ids_res = {chat.id for chat in chat_list_res}
    assert chat_ids_res == set(chat_id_list)


async def test_get_joined_chat_list_empty(
    chat_manager: ChatManager, async_session: AsyncSession
):
    """
    get_joined_chat_list() returns empty list if user hasn't joined any chats.
    """
    # Create user, chats and add user to these chats
    user_id = uuid.uuid4()
    async_session.add(User(id=user_id, name="User"))
    await async_session.commit()

    # Call chat_manager.get_joined_chat_list() and check results
    chat_list_res = await chat_manager.get_joined_chat_list(current_user_id=user_id)
    assert len(chat_list_res) == 0


@pytest.mark.parametrize("failure_method", ("get_joined_chat_list",))
async def test_get_joined_chat_list_repo_failure(
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    get_joined_chat_list() raises RepositoryError in case of repository failure
    """
    user_id = uuid.uuid4()

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call get_joined_chat_list() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.get_joined_chat_list(current_user_id=user_id)
