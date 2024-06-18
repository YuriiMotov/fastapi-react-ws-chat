import random
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas import client_packet as cli_p
from backend.schemas import server_packet as srv_p
from backend.schemas.chat_message import ChatUserMessageCreateSchema
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import (
    EventBrokerError,
    RepositoryError,
)
from backend.services.ws_chat_server import _process_ws_client_request_packet

# ---------------------------------------------------------------------------------
# CMDGetJoinedChats


async def test_process_ws_client_request_get_joined_chats(
    chat_manager: ChatManager, async_session: AsyncSession
):
    user_id = uuid.uuid4()
    chat_ids = [uuid.uuid4() for _ in range(3)]
    current_user_id = user_id

    for chat_id in chat_ids:
        async_session.add(Chat(id=chat_id, title="my chat", owner_id=current_user_id))
        async_session.add(UserChatLink(chat_id=chat_id, user_id=user_id))

    await async_session.commit()

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDGetJoinedChats(),
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespGetJoinedChatList) is True
    if isinstance(response.data, srv_p.SrvRespGetJoinedChatList):
        assert len(response.data.chats) == len(chat_ids)
        for chat in response.data.chats:
            assert chat.id in chat_ids


# ---------------------------------------------------------------------------------
# CMDAddUserToChat


async def test_process_ws_client_request_add_user_to_chat(
    chat_manager: ChatManager,
    async_session: AsyncSession,
    event_broker_user_id_list: list[uuid.UUID],
):

    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    current_user_id = user_id

    async_session.add(Chat(id=chat_id, title="my chat", owner_id=current_user_id))
    await async_session.commit()

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDAddUserToChat(chat_id=chat_id, user_id=user_id),
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespSucessNoBody) is True
    user_chat_link = await async_session.scalar(
        select(UserChatLink)
        .where(UserChatLink.chat_id == chat_id)
        .where(UserChatLink.user_id == user_id)
    )
    assert user_chat_link is not None
    assert isinstance(user_chat_link, UserChatLink)


# ---------------------------------------------------------------------------------
# CMDGetMessages


async def test_process_ws_client_request_get_messages(
    chat_manager: ChatManager, async_session: AsyncSession
):

    user_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    current_user_id = user_id
    messages: list[ChatUserMessage] = []
    for _ in range(3):
        messages.append(
            ChatUserMessage(
                chat_id=chat_id, text=f"msg {uuid.uuid4()}", sender_id=another_user_id
            )
        )
    user = User(id=user_id, name="user")
    chat = Chat(id=chat_id, title="my chat", owner_id=current_user_id)
    user_chat = UserChatLink(user_id=user_id, chat_id=chat_id)
    async_session.add_all((user, chat, user_chat, *messages))
    await async_session.commit()

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000), data=cli_p.CMDGetMessages(chat_id=chat_id)
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespGetMessages) is True
    if isinstance(response.data, srv_p.SrvRespGetMessages):
        resp_messages = response.data.messages
    assert len(resp_messages) == len(messages)
    expected_message_texts = {msg.text for msg in messages}
    for resp_msg in resp_messages:
        assert resp_msg.text in expected_message_texts


# ---------------------------------------------------------------------------------
# CMDSendMessage


async def test_process_ws_client_request_send_message(
    chat_manager: ChatManager,
    async_session: AsyncSession,
    event_broker_user_id_list: list[uuid.UUID],
):
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    current_user_id = user_id

    async_session.add(Chat(id=chat_id, title="my chat", owner_id=current_user_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user_id))
    await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )
    request = cli_p.ClientPacket(
        id=random.randint(1, 10000), data=cli_p.CMDSendMessage(message=message)
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespSucessNoBody) is True
    message_in_db = await async_session.scalar(
        select(ChatUserMessage)
        .where(ChatUserMessage.chat_id == chat_id)
        .where(ChatUserMessage.sender_id == user_id)
    )
    assert message_in_db is not None
    assert isinstance(message_in_db, ChatUserMessage)


# ---------------------------------------------------------------------------------
# CMDEditMessage


async def test_process_ws_client_request__edit_message__success(
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    user_id = event_broker_user_id_list[0]
    current_user_id = user_id
    message_id = random.randint(1, 1000000)
    new_text = "new text"

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDEditMessage(message_id=message_id, text=new_text),
    )

    with patch.object(chat_manager, "edit_message") as patched:
        response = await _process_ws_client_request_packet(
            chat_manager=chat_manager, packet=request, current_user_id=current_user_id
        )
        patched.assert_awaited_once_with(
            current_user_id=current_user_id, message_id=message_id, text=new_text
        )

    assert isinstance(response.data, srv_p.SrvRespSucessNoBody) is True


@pytest.mark.parametrize("exception", (RepositoryError("-"), EventBrokerError("-")))
async def test_process_ws_client_request__edit_message__failure(
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
    exception: Exception,
):
    user_id = event_broker_user_id_list[0]
    current_user_id = user_id
    message_id = random.randint(1, 1000000)
    new_text = "new text"

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDEditMessage(message_id=message_id, text=new_text),
    )

    with patch.object(
        chat_manager, "edit_message", new=AsyncMock(side_effect=exception)
    ) as patched:
        response = await _process_ws_client_request_packet(
            chat_manager=chat_manager, packet=request, current_user_id=current_user_id
        )
        patched.assert_awaited_once_with(
            current_user_id=current_user_id, message_id=message_id, text=new_text
        )

    assert isinstance(response.data, srv_p.SrvRespError) is True


# ---------------------------------------------------------------------------------
# CMDAcknowledgeEvents


async def test_process_ws_client_request__acknowledge_events__success(
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    user_id = event_broker_user_id_list[0]
    current_user_id = user_id

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDAcknowledgeEvents(),
    )

    with patch.object(chat_manager, "acknowledge_events") as patched:
        response = await _process_ws_client_request_packet(
            chat_manager=chat_manager, packet=request, current_user_id=current_user_id
        )
        patched.assert_awaited_once_with(current_user_id=current_user_id)

    assert isinstance(response.data, srv_p.SrvRespSucessNoBody) is True


@pytest.mark.parametrize("exception", (RepositoryError("-"), EventBrokerError("-")))
async def test_process_ws_client_request__acknowledge_events__failure(
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
    exception: Exception,
):
    user_id = event_broker_user_id_list[0]
    current_user_id = user_id

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDAcknowledgeEvents(),
    )

    with patch.object(
        chat_manager, "acknowledge_events", new=AsyncMock(side_effect=exception)
    ) as patched:
        response = await _process_ws_client_request_packet(
            chat_manager=chat_manager, packet=request, current_user_id=current_user_id
        )
        patched.assert_awaited_once_with(current_user_id=current_user_id)

    assert isinstance(response.data, srv_p.SrvRespError) is True


# ---------------------------------------------------------------------------------
# CMDGetFirstCircleListUpdates


async def test_process_ws_client_request_get_first_circle_list(
    chat_manager: ChatManager,
    async_session: AsyncSession,
    event_broker_user_id_list: list[uuid.UUID],
):
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    current_user_id = user_id

    user = User(id=user_id, name="user 1", hashed_password="")
    chat = Chat(id=chat_id, title="my chat", owner_id=current_user_id)
    user_chat_link = UserChatLink(user_id=user_id, chat_id=chat_id)
    async_session.add_all((user, chat, user_chat_link))
    await async_session.commit()

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDGetFirstCircleListUpdates(),
    )

    with patch.object(chat_manager, "get_first_circle_user_list") as patched:
        response = await _process_ws_client_request_packet(
            chat_manager=chat_manager, packet=request, current_user_id=current_user_id
        )

        assert isinstance(response.data, srv_p.SrvRespSucessNoBody) is True
        patched.assert_awaited_once_with(
            current_user_id=current_user_id,
            full=True,
        )
