import uuid
from unittest.mock import Mock, patch

import pytest

from backend.schemas.chat import ChatCreateSchema
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    EventBrokerError,
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo
from backend.services.event_broker.event_broker_exc import EventBrokerException
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker


async def test_create_chat__evokes_add_chat_and_add_user_to_chat(
    chat_manager: ChatManager,
):
    """
    create_chat() method evokes chat_repo.add_chat() and chat_manager.add_user_to_chat()
    methods with corresponding params.
    """
    current_user_id = uuid.uuid4()
    chat_data = ChatCreateSchema(
        id=uuid.uuid4(),
        title=f"chat {uuid.uuid4()}",
        owner_id=current_user_id,
    )

    with patch.object(
        SQLAlchemyChatRepo, "add_chat", return_value=chat_data
    ) as add_chat_patched:
        with patch.object(chat_manager, "add_user_to_chat") as add_user_patched:
            await chat_manager.create_chat(
                current_user_id=current_user_id, chat_data=chat_data
            )
            add_chat_patched.assert_awaited_once_with(chat=chat_data)
            add_user_patched.assert_awaited_once_with(
                current_user_id=current_user_id,
                user_id=current_user_id,
                chat_id=chat_data.id,
            )


async def test_create_chat__unauthorized_error(
    chat_manager: ChatManager,
):
    """
    create_chat() method raises UnauthorizedAction if the owner_id is not equal to
    current_user_id.
    """
    current_user_id = uuid.uuid4()
    chat_data = ChatCreateSchema(
        id=uuid.uuid4(),
        title=f"chat {uuid.uuid4()}",
        owner_id=uuid.uuid4(),
    )

    with pytest.raises(
        UnauthorizedAction, match="Can't create chat on behalf of another user"
    ):
        await chat_manager.create_chat(
            current_user_id=current_user_id, chat_data=chat_data
        )


@pytest.mark.parametrize("failure_method", ("add_chat", "add_user_to_chat"))
async def test_create_chat__repo_failure(
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    create_chat() raises RepositoryError in case of repository failure
    """
    current_user_id = uuid.uuid4()
    chat_data = ChatCreateSchema(
        id=uuid.uuid4(),
        title=f"chat {uuid.uuid4()}",
        owner_id=current_user_id,
    )

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call create_chat() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.create_chat(
                current_user_id=current_user_id, chat_data=chat_data
            )


@pytest.mark.parametrize("failure_method", ("post_event",))
async def test_create_chat__event_broker_failure(
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    create_chat() raises EventBrokerError if EventBroker raises error
    """
    current_user_id = uuid.uuid4()
    chat_data = ChatCreateSchema(
        id=uuid.uuid4(),
        title=f"chat {uuid.uuid4()}",
        owner_id=current_user_id,
    )

    # Patch InMemoryEventBroker.{failure_method} method so that it always raises
    # EventBrokerException
    with patch.object(
        InMemoryEventBroker,
        failure_method,
        new=Mock(side_effect=EventBrokerException()),
    ):
        # Call add_user_to_chat() and check that it raises EventBrokerError
        with pytest.raises(EventBrokerError):
            await chat_manager.create_chat(
                current_user_id=current_user_id, chat_data=chat_data
            )
