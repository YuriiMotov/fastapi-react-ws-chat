import random
import uuid
from asyncio import sleep as asleep
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient, WebSocketTestSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user_chat_link import UserChatLink
from backend.schemas.chat_message import (
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from backend.schemas.client_packet import (
    ClientPacket,
    CMDAddUserToChat,
    CMDGetJoinedChats,
    CMDGetMessages,
    CMDSendMessage,
)
from backend.schemas.server_packet import (
    ServerPacket,
    SrvEventList,
    SrvRespError,
    SrvRespGetJoinedChatList,
    SrvRespGetMessages,
    SrvRespSucessNoBody,
)
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import RepositoryError
from backend.services.message_broker.in_memory_message_broker import (
    InMemoryMessageBroker,
)

# ---------------------------------------------------------------------------------
# Tests for websocket connect\disconnect


async def test_ws_chat_connect(client: TestClient):
    user_id = uuid.uuid4()
    websocket: WebSocketTestSession
    with client.websocket_connect(
        f"/ws/chat?user_id={user_id}"
    ) as websocket:  # noqa: F841
        await asleep(0.1)


async def test_ws_chat_subscribe_on_connect(
    client: TestClient, message_broker: InMemoryMessageBroker
):
    user_id = uuid.uuid4()
    websocket: WebSocketTestSession
    mocked_subscribe = AsyncMock(wraps=message_broker.subscribe_list)
    with patch.object(InMemoryMessageBroker, "subscribe_list", new=mocked_subscribe):
        with client.websocket_connect(
            f"/ws/chat?user_id={user_id}"
        ) as websocket:  # noqa: F841
            await asleep(0.1)
            # Check that chat_manager.message_broker.subscribe_list() was called
            mocked_subscribe.assert_awaited_with(user_id=user_id, channels=[])


async def test_ws_chat_unsubscribe_on_connection_close(client: TestClient):
    user_id = uuid.uuid4()
    websocket: WebSocketTestSession
    mocked_unsubscribe = AsyncMock()
    with patch.object(InMemoryMessageBroker, "unsubscribe", new=mocked_unsubscribe):
        with client.websocket_connect(
            f"/ws/chat?user_id={user_id}"
        ) as websocket:  # noqa: F841
            await asleep(0.1)
        # Check that chat_manager.message_broker.unsubscribe() was called
        mocked_unsubscribe.assert_awaited_with(user_id=user_id)


# ---------------------------------------------------------------------------------
# Tests for CMDGetJoinedChats command


async def test_ws_chat_get_joined_chats__success(
    client: TestClient, async_session: AsyncSession
):
    current_user_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    # Create chats, add user to chats
    chat_ids = [uuid.uuid4() for _ in range(3)]
    for chat_id in chat_ids:
        async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
        async_session.add(UserChatLink(chat_id=chat_id, user_id=current_user_id))
    await async_session.commit()

    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())

        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespGetJoinedChatList)
        if isinstance(srv_packet.data, SrvRespGetJoinedChatList):
            assert len(srv_packet.data.chats) == len(chat_ids)


def test_ws_chat_get_joined_chats__empty_list(client: TestClient):
    current_user_id = uuid.uuid4()
    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())

        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespGetJoinedChatList)
        if isinstance(srv_packet.data, SrvRespGetJoinedChatList):
            assert len(srv_packet.data.chats) == 0


def test_ws_chat_get_joined_chats__error(client: TestClient):
    current_user_id = uuid.uuid4()
    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession

    raise_error = RepositoryError(detail="repo error")
    with patch.object(
        ChatManager,
        "get_joined_chat_list",
        new=Mock(side_effect=raise_error),
    ):
        with client.websocket_connect(
            f"/ws/chat?user_id={current_user_id}"
        ) as websocket:
            websocket.send_text(client_packet.model_dump_json())
            resp_str = websocket.receive_text()

            srv_packet = ServerPacket.model_validate_json(resp_str)
            assert srv_packet.request_packet_id == client_packet.id
            assert isinstance(srv_packet.data, SrvRespError)
            if isinstance(srv_packet.data, SrvRespError):
                assert srv_packet.data.error_data.error_code == raise_error.error_code
                assert srv_packet.data.error_data.detail == raise_error.detail


# ---------------------------------------------------------------------------------
# Tests for CMDAddUserToChat command


async def test_ws_chat_add_user_to_chat__success(
    client: TestClient, async_session: AsyncSession
):
    current_user_id = uuid.uuid4()
    owner_id = current_user_id
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    # Create chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    await async_session.commit()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=another_user_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespSucessNoBody)


def test_ws_chat_add_user_to_chat__chat_doesnt_exist_error(client: TestClient):
    current_user_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=another_user_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession

    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespError)
        if isinstance(srv_packet.data, SrvRespError):
            assert srv_packet.data.error_data.error_code == "CHAT_MANAGER_GENERAL_ERROR"
            assert (
                srv_packet.data.error_data.detail
                == f"Chat with ID={chat_id} doesn't exist"
            )


async def test_ws_chat_add_user_to_chat__unauthorized_error(
    client: TestClient, async_session: AsyncSession
):
    current_user_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    # Create chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    await async_session.commit()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=another_user_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession

    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespError)
        if isinstance(srv_packet.data, SrvRespError):
            assert srv_packet.data.error_data.error_code == "CHAT_MANAGER_GENERAL_ERROR"
            assert "unauthorized to add users to" in srv_packet.data.error_data.detail


# ---------------------------------------------------------------------------------
# Tests for CMDSendMessage command


async def test_ws_chat_send_message__success(
    client: TestClient, async_session: AsyncSession
):
    current_user_id = uuid.uuid4()
    owner_id = current_user_id
    chat_id = uuid.uuid4()
    # Create chat, add user to chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=current_user_id))
    await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=current_user_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespSucessNoBody)

    message_db = await async_session.scalar(
        select(ChatUserMessage)
        .where(ChatUserMessage.chat_id == chat_id)
        .where(ChatUserMessage.sender_id == current_user_id)
    )
    assert message_db is not None
    assert message_db.text == message.text


async def test_ws_chat_send_message__unauthorized_error(
    client: TestClient, async_session: AsyncSession
):
    current_user_id = uuid.uuid4()
    owner_id = current_user_id
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    # Create chat, add user to chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=current_user_id))
    await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=another_user_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespError)
        if isinstance(srv_packet.data, SrvRespError):
            assert srv_packet.data.error_data.error_code == "CHAT_MANAGER_GENERAL_ERROR"
            assert (
                "Can't send message on behalf of another user"
                in srv_packet.data.error_data.detail
            )

    message_db = await async_session.scalar(
        select(ChatUserMessage)
        .where(ChatUserMessage.chat_id == chat_id)
        .where(ChatUserMessage.sender_id == current_user_id)
    )
    assert message_db is None


async def test_ws_chat_send_message__unauthorized_not_chat_member_error(
    client: TestClient, async_session: AsyncSession
):
    current_user_id = uuid.uuid4()
    owner_id = current_user_id
    chat_id = uuid.uuid4()
    # Create chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=current_user_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespError)
        if isinstance(srv_packet.data, SrvRespError):
            assert srv_packet.data.error_data.error_code == "CHAT_MANAGER_GENERAL_ERROR"
            assert "is not a member of chat" in srv_packet.data.error_data.detail

    message_db = await async_session.scalar(
        select(ChatUserMessage)
        .where(ChatUserMessage.chat_id == chat_id)
        .where(ChatUserMessage.sender_id == current_user_id)
    )
    assert message_db is None


# ---------------------------------------------------------------------------------
# Tests for CMDGetMessages command


async def test_ws_chat_get_messages__success(
    client: TestClient, async_session: AsyncSession
):
    current_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    # Create messages
    messages = [
        ChatUserMessage(
            chat_id=chat_id, text=f"message {uuid.uuid4()}", sender_id=current_user_id
        )
        for _ in range(3)
    ]
    async_session.add_all(messages)
    await async_session.commit()

    expected_messages = list(reversed(messages))
    cmd = CMDGetMessages(chat_id=chat_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespGetMessages)
        if isinstance(srv_packet.data, SrvRespGetMessages):
            assert len(srv_packet.data.messages) == len(messages)
            for i in range(len(messages)):
                msg_obj = ChatUserMessageSchema.model_validate_json(
                    srv_packet.data.messages[i]
                )
                assert msg_obj.text == expected_messages[i].text


async def test_ws_chat_get_messages__success_empty_list(client: TestClient):
    current_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    cmd = CMDGetMessages(chat_id=chat_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={current_user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())
        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespGetMessages)
        if isinstance(srv_packet.data, SrvRespGetMessages):
            assert len(srv_packet.data.messages) == 0


def test_ws_chat_get_messages__error(client: TestClient):
    current_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    cmd = CMDGetMessages(chat_id=chat_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession

    raise_error = RepositoryError(detail="repo error")
    with patch.object(
        ChatManager,
        "get_message_list",
        new=Mock(side_effect=raise_error),
    ):
        with client.websocket_connect(
            f"/ws/chat?user_id={current_user_id}"
        ) as websocket:
            websocket.send_text(client_packet.model_dump_json())
            resp_str = websocket.receive_text()

            srv_packet = ServerPacket.model_validate_json(resp_str)
            assert srv_packet.request_packet_id == client_packet.id
            assert isinstance(srv_packet.data, SrvRespError)
            if isinstance(srv_packet.data, SrvRespError):
                assert srv_packet.data.error_data.error_code == raise_error.error_code
                assert srv_packet.data.error_data.detail == raise_error.detail


# ---------------------------------------------------------------------------------
# Test receiving events


async def test_ws_chat_receive_events__user_message(
    client: TestClient, async_session: AsyncSession
):
    # Add user1 and user2 to chat
    owner_id = uuid.uuid4()
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user1_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user2_id))
    await async_session.commit()

    # Send message from user1 to chat. Check that both users receive message
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=user1_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    user1_websocket: WebSocketTestSession
    user2_websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={user1_id}") as user1_websocket:
        with client.websocket_connect(
            f"/ws/chat?user_id={user2_id}"
        ) as user2_websocket:
            user1_websocket.send_text(client_packet.model_dump_json())
            resp_str = user1_websocket.receive_text()
            srv_packet = ServerPacket.model_validate_json(resp_str)
            assert isinstance(srv_packet.data, SrvRespSucessNoBody)  # Msg was sent

            await asleep(0.1)

            # Receive user1's events
            resp_str = user1_websocket.receive_text()
            srv_packet = ServerPacket.model_validate_json(resp_str)
            assert isinstance(srv_packet.data, SrvEventList)
            if isinstance(srv_packet.data, SrvEventList):
                assert len(srv_packet.data.events) == 1
                received_msg = ChatUserMessageSchema.model_validate_json(
                    srv_packet.data.events[0]
                )
                assert received_msg.text == message.text

            # Receive user2's events
            resp_str = user2_websocket.receive_text()
            srv_packet = ServerPacket.model_validate_json(resp_str)
            assert isinstance(srv_packet.data, SrvEventList)
            if isinstance(srv_packet.data, SrvEventList):
                assert len(srv_packet.data.events) == 1
                received_msg = ChatUserMessageSchema.model_validate_json(
                    srv_packet.data.events[0]
                )
                assert received_msg.text == message.text
