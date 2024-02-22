import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat_message import ChatUserMessage
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import RepositoryError
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.chat_repo.sqla_chat_repo import SQLAlchemyChatRepo


async def test_get_message_list_success(
    async_session: AsyncSession, chat_manager: ChatManager
):
    """
    Successful execution of get_message_list() returns list of messages from DB.
    """

    user_id = uuid.uuid4()
    chat_1_id = uuid.uuid4()
    chat_2_id = uuid.uuid4()
    # Add messages to chat_1 and chat_2
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

    # Call chat_manager.get_message_list() and check result
    messages_res = await chat_manager.get_message_list(chat_id=chat_1_id)
    assert len(messages_res) == len(chat_1_messages)
    message_textx_res = {msg.text for msg in messages_res}
    assert message_textx_res == set(chat_1_messages)


@pytest.mark.parametrize("order_desc", (True, False))
@pytest.mark.parametrize("start_id", (-1, 1, 2))
@pytest.mark.parametrize("limit", (100, 1))
async def test_get_message_list_order_and_filter(
    order_desc: bool, start_id: int, limit: int, chat_manager: ChatManager
):
    """
    Chack that calling get_message_list() leads to calling chat_repo.get_message_list()
    with the same parameters
    """
    chat_id = uuid.uuid4()

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
            chat_id=chat_id, start_id=start_id, order_desc=order_desc, limit=limit
        )
        mocked_get_message_list.assert_awaited_with(
            chat_id=chat_id, start_id=start_id, order_desc=order_desc, limit=limit
        )


@pytest.mark.parametrize("failure_method", ("get_message_list",))
async def test_get_message_list_repo_failure(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    failure_method: str,
):
    """
    get_message_list() raises RepositoryError in case of repository failure
    """
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    # Add messages to chat_1
    messages = [f"msg {uuid.uuid4()}" for _ in range(3)]
    for message in messages:
        async_session.add(
            ChatUserMessage(chat_id=chat_id, text=message, sender_id=user_id)
        )
    await async_session.commit()

    # Patch SQLAlchemyChatRepo.{failure_method} method so that it always raises
    # ChatRepoException
    with patch.object(
        SQLAlchemyChatRepo,
        failure_method,
        new=Mock(side_effect=ChatRepoException()),
    ):
        # Call get_message_list() and check that it raises RepositoryError
        with pytest.raises(RepositoryError):
            await chat_manager.get_message_list(chat_id=chat_id)
