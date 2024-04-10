import uuid
from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo


@pytest.fixture()
async def user_chats_messages(async_session: AsyncSession):
    user_id = uuid.uuid4()
    chat_1_id = uuid.uuid4()
    chat_2_id = uuid.uuid4()
    # Create user, chats, add user to chats, add messages to chats
    user = User(id=user_id, name="user")
    chat_1 = Chat(id=chat_1_id, title="chat 1", owner_id=user_id)
    chat_2 = Chat(id=chat_2_id, title="chat 2", owner_id=user_id)
    user_chat_1 = UserChatLink(user_id=user_id, chat_id=chat_1_id)
    user_chat_2 = UserChatLink(user_id=user_id, chat_id=chat_2_id)
    async_session.add_all((user, chat_1, chat_2, user_chat_1, user_chat_2))
    chat_1_messages = [f"msg {uuid.uuid4()}" for _ in range(3)]
    for message in chat_1_messages:
        async_session.add(
            ChatUserMessage(chat_id=chat_1_id, text=message, sender_id=user_id)
        )
    chat_2_messages = [f"msg {uuid.uuid4()}" for _ in range(3)]
    for message in chat_2_messages:
        async_session.add(
            ChatUserMessage(chat_id=chat_2_id, text=message, sender_id=user_id)
        )
    await async_session.commit()
    return {
        "user_id": user_id,
        "chat_1_id": chat_1_id,
        "chat_2_id": chat_2_id,
        "chat_1_messages": chat_1_messages,
        "chat_2_messages": chat_2_messages,
    }


async def test_get_message_list_success(
    chat_manager: ChatManager, user_chats_messages: dict[str, Any]
):
    """
    Successful execution of get_message_list() returns list of messages from DB.
    """
    user_id = cast(uuid.UUID, user_chats_messages["user_id"])
    chat_1_id = cast(uuid.UUID, user_chats_messages["chat_1_id"])
    chat_1_messages = cast(list[str], user_chats_messages["chat_1_messages"])

    # Call chat_manager.get_message_list() and check result
    messages_res = await chat_manager.get_message_list(
        current_user_id=user_id, chat_id=chat_1_id
    )
    assert len(messages_res) == len(chat_1_messages)
    message_textx_res = {msg.text for msg in messages_res}
    assert message_textx_res == set(chat_1_messages)


@pytest.mark.parametrize("order_desc", (True, False))
@pytest.mark.parametrize("start_id", (-1, 1, 2))
@pytest.mark.parametrize("limit", (100, 1))
async def test_get_message_list_order_and_filter(
    order_desc: bool,
    start_id: int,
    limit: int,
    chat_manager: ChatManager,
    user_chats_messages: dict[str, Any],
):
    """
    Chack that calling get_message_list() leads to calling chat_repo.get_message_list()
    with the same parameters
    """
    user_id = cast(uuid.UUID, user_chats_messages["user_id"])
    chat_id = cast(uuid.UUID, user_chats_messages["chat_1_id"])

    # Mock SQLAlchemyChatRepo.get_message_list() method,
    # call chat_manager.get_message_list and
    # check that SQLAlchemyChatRepo.get_message_list() was called with the same params
    mocked_get_message_list = AsyncMock(return_value=[])
    with patch.object(
        SQLAlchemyChatRepo,
        "get_message_list",
        new=mocked_get_message_list,
    ):
        await chat_manager.get_message_list(
            current_user_id=user_id,
            chat_id=chat_id,
            start_id=start_id,
            order_desc=order_desc,
            limit=limit,
        )
        mocked_get_message_list.assert_awaited_with(
            chat_id=chat_id,
            start_id=start_id,
            order_desc=order_desc,
            limit=limit,
        )


async def test_get_message_list__unauthorized_not_chat_member(
    chat_manager: ChatManager, user_chats_messages: dict[str, Any]
):
    """
    Execution of get_message_list() raises UnauthorizedAction if user is not a member of
    this chat.
    """
    user_id = cast(uuid.UUID, user_chats_messages["user_id"])
    chat_id = uuid.uuid4()

    # Call chat_manager.get_message_list() and check that UnauthorizedAction is raised
    with pytest.raises(UnauthorizedAction):
        await chat_manager.get_message_list(current_user_id=user_id, chat_id=chat_id)


@pytest.mark.parametrize("failure_method", ("get_message_list",))
async def test_get_message_list_repo_failure(
    chat_manager: ChatManager,
    failure_method: str,
    user_chats_messages: dict[str, Any],
):
    """
    get_message_list() raises RepositoryError in case of repository failure
    """
    user_id = cast(uuid.UUID, user_chats_messages["user_id"])
    chat_id = cast(uuid.UUID, user_chats_messages["chat_1_id"])

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call get_message_list() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.get_message_list(
                current_user_id=user_id, chat_id=chat_id
            )
