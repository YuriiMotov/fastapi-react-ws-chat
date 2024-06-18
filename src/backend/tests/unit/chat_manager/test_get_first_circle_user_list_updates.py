from typing import Any
from unittest.mock import Mock, patch

import pytest

from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import RepositoryError
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo


async def test_get_first_circle_user_list_updates__success(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
):
    """
    _get_first_circle_user_list_updates() returns updates in list of users in chats,
    where this user is a member.
    """
    user_1 = u_c["user_1"]
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_1"].id, chat_id=u_c["chat_1"].id
    )
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_1"].id, chat_id=u_c["chat_2"].id
    )
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_2"].id, chat_id=u_c["chat_1"].id
    )

    # Call _get_first_circle_user_list_updates()
    first_circle_user_list = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1.id
    )
    assert len(first_circle_user_list) == 2

    # Add one more user to the first circle and call _get_first_circle_user_list_updates
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_3"].id, chat_id=u_c["chat_1"].id
    )
    list_updates = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1.id
    )
    assert len(list_updates) == 1
    assert list_updates[0].id == u_c["user_3"].id


async def test_get_first_circle_user_list_updates__empty_list(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
):
    """
    _get_first_circle_user_list_updates() returns empty list if nothing has changed
    since last call.
    """
    user_1 = u_c["user_1"]
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_1"].id, chat_id=u_c["chat_1"].id
    )
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_2"].id, chat_id=u_c["chat_1"].id
    )

    # Call _get_first_circle_user_list_updates()
    first_circle_user_list = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1.id
    )
    assert len(first_circle_user_list) == 2

    list_updates = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1.id
    )
    assert len(list_updates) == 0


async def test_get_first_circle_user_list_updates__third_call(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
):
    """
    _get_first_circle_user_list_updates() returns updates in list of users in chats,
    where this user is a member.
    Check first circle user list three times, adding one more user every time.
    """
    user_1 = u_c["user_1"]
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_1"].id, chat_id=u_c["chat_1"].id
    )

    # Call _get_first_circle_user_list_updates()
    first_circle_user_list = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1.id
    )
    assert len(first_circle_user_list) == 1

    # Add one more user to the first circle and call _get_first_circle_user_list_updates
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_2"].id, chat_id=u_c["chat_1"].id
    )
    list_updates = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1.id
    )
    assert len(list_updates) == 1
    assert list_updates[0].id == u_c["user_2"].id

    # Add one more user to the first circle and call _get_first_circle_user_list_updates
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_3"].id, chat_id=u_c["chat_1"].id
    )
    list_updates = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1.id
    )
    assert len(list_updates) == 1
    assert list_updates[0].id == u_c["user_3"].id


@pytest.mark.parametrize("failure_method", ("get_user_list", "get_joined_chat_ids"))
async def test_get_first_circle_user_list_updates__repo_failure(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
    failure_method: str,
):
    """
    _get_first_circle_user_list_updates() raises RepositoryError in case of
    repository failure.
    """
    user_1 = u_c["user_1"]
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_1"].id, chat_id=u_c["chat_1"].id
    )

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call _get_first_circle_user_list_updates() and check that it
        # raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager._get_first_circle_user_list_updates(
                current_user_id=user_1.id
            )
