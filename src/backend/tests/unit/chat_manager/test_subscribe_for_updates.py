import uuid
from typing import Any
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
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


async def test_subscribe_for_updates(
    chat_manager: ChatManager,
    async_session: AsyncSession,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    subscribe_for_updates() subscribes user to events in all their chats
    """
    # Create user, chats and add user to these chats
    user_id = event_broker_user_id_list[0]
    async_session.add(User(id=user_id, name="User"))
    chat_owner_id = event_broker_user_id_list[1]
    chat_id_list = [uuid.uuid4() for _ in range(3)]
    objects: list[Any] = []
    for chat_id in chat_id_list:
        objects.append(Chat(id=chat_id, title="chat", owner_id=chat_owner_id))
        objects.append(UserChatLink(user_id=user_id, chat_id=chat_id))
    async_session.add_all(objects)
    await async_session.commit()

    # Call subscribe_for_updates()
    await chat_manager.subscribe_for_updates(current_user_id=user_id)

    # Check that user was subscribed for events in all their chats
    for chat_id in chat_id_list:
        # Post one message to every chat
        await chat_manager.event_broker._post_event_str(
            channel=channel_code("chat", chat_id), event=str(chat_id)
        )
    events = await chat_manager.event_broker._get_events_str(user_id=user_id)
    assert len(events) == len(chat_id_list)
    assert set(events) == set(map(str, chat_id_list))


@pytest.mark.parametrize("failure_method", ("get_joined_chat_ids",))
async def test_subscribe_for_updates_repo_failure(
    chat_manager: ChatManager, failure_method: str
):
    """
    subscribe_for_updates() raises RepositoryError if ChatRepo raises error
    """
    user_id = uuid.uuid4()

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call subscribe_for_updates() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.subscribe_for_updates(current_user_id=user_id)


@pytest.mark.parametrize("failure_method", ("subscribe_list",))
async def test_subscribe_for_updates_event_broker_failure(
    chat_manager: ChatManager, failure_method: str
):
    """
    subscribe_for_updates() raises EventBrokerError if EventBroker raises error
    """
    user_id = uuid.uuid4()

    # Patch InMemoryEventBroker.{failure_method} method so that it always raises
    # EventBrokerException
    with patch.object(
        InMemoryEventBroker,
        failure_method,
        new=Mock(side_effect=EventBrokerException()),
    ):
        # Call subscribe_for_updates() and check that it raises EventBrokerError
        with pytest.raises(EventBrokerError):
            await chat_manager.subscribe_for_updates(current_user_id=user_id)
