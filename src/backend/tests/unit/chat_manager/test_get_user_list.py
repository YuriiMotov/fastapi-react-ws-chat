from typing import Any
from unittest.mock import Mock, patch

import pytest

from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import RepositoryError
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo


@pytest.mark.parametrize("offset", (None, 1, 10))
@pytest.mark.parametrize("limit", (None, 1, 10))
async def test_get_user_list__success(
    chat_manager: ChatManager,
    offset: int | None,
    limit: int | None,
):
    """
    get_user_list() calls chat_repo.get_user_list() with the corresponding params.
    """
    offset_real = offset if (offset is not None) else 0
    limit_real = limit if (limit is not None) else 10

    params: dict[str, Any] = {"name_filter": "n"}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    with patch.object(SQLAlchemyChatRepo, "get_user_list") as patched:
        await chat_manager.get_user_list(**params)
        patched.assert_awaited_once_with(
            name_filter="n",
            limit=limit_real,
            offset=offset_real,
        )


@pytest.mark.parametrize("failure_method", ("get_user_list",))
async def test_get_user_list__repo_failure(
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    get_user_list() raises RepositoryError in case of repository failure.
    """
    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call get_user_list() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.get_user_list(name_filter="m")
