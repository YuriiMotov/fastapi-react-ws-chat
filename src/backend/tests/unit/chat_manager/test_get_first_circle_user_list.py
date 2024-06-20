from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

from backend.schemas.event import FirstCircleUserListUpdate
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    EventBrokerError,
    RepositoryError,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.event_broker.event_broker_exc import EventBrokerException
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker


async def test_get_first_circle_user_list__success(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
):
    """
    get_first_circle_user_list() calls EventBroker.post_event().
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

    with patch.object(InMemoryEventBroker, "post_event") as patched:
        await chat_manager.get_first_circle_user_list(current_user_id=user_1.id)
        patched.assert_awaited_once()
        assert patched.await_args is not None
        if patched.await_args is not None:
            call_kwargs = patched.await_args.kwargs
            assert call_kwargs["channel"] == channel_code("user", user_1.id)
            assert isinstance(call_kwargs["event"], FirstCircleUserListUpdate)
            event = cast(FirstCircleUserListUpdate, call_kwargs["event"])
            assert len(event.users) == 2
            assert event.users[0].id in (user_1.id, u_c["user_2"].id)
            assert event.users[1].id in (user_1.id, u_c["user_2"].id)
            assert event.users[0].id != event.users[1].id


async def test_get_first_circle_user_list__empty_list(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
):
    """
    get_first_circle_user_list() doesn't call EventBroker.post_event() if there ra no
    new users in the list
    """
    user_1 = u_c["user_1"]

    with patch.object(InMemoryEventBroker, "post_event") as patched:
        await chat_manager.get_first_circle_user_list(current_user_id=user_1.id)
        patched.assert_not_awaited()


@pytest.mark.parametrize("failure_method", ("get_user_list", "get_joined_chat_ids"))
async def test_get_first_circle_user_list__repo_failure(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
    failure_method: str,
):
    """
    get_first_circle_user_list() raises RepositoryError in case of
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
        # Call get_first_circle_user_list() and check that it
        # raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.get_first_circle_user_list(current_user_id=user_1.id)


@pytest.mark.parametrize("failure_method", ("post_event",))
async def test_get_first_circle_user_list__event_broker_failure(
    chat_manager: ChatManager,
    u_c: dict[str, Any],
    failure_method: str,
):
    """
    get_first_circle_user_list() raises EventBrokerError in case of
    Event broker failure.
    """
    user_1 = u_c["user_1"]
    await chat_manager.add_user_to_chat(
        current_user_id=user_1.id, user_id=u_c["user_1"].id, chat_id=u_c["chat_1"].id
    )

    # Patch InMemoryEventBroker.{failure_method} method so that it always raises
    # EventBrokerException
    with patch.object(
        InMemoryEventBroker,
        failure_method,
        new=Mock(side_effect=EventBrokerException()),
    ):
        # Call get_first_circle_user_list() and check that it
        # raises EventBrokerError
        with pytest.raises(EventBrokerError):
            await chat_manager.get_first_circle_user_list(current_user_id=user_1.id)
