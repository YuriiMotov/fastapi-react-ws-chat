import random
import uuid
from unittest.mock import Mock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient, WebSocketTestSession

from backend.models.chat import Chat
from backend.models.user_chat_link import UserChatLink
from backend.schemas.client_packet import ClientPacket, CMDGetJoinedChats
from backend.schemas.server_packet import (
    ServerPacket,
    SrvRespError,
    SrvRespGetJoinedChatList,
)
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.chat_manager_exc import RepositoryError


def test_ws_chat_connect(client: TestClient):
    user_id = uuid.uuid4()
    websocket: WebSocketTestSession
    with client.websocket_connect(
        f"/ws/chat?user_id={user_id}"
    ) as websocket:  # noqa: F841
        pass


# ---------------------------------------------------------------------------------
# Tests for CMDGetJoinedChats command


async def test_ws_chat_get_joined_chats__success(
    client: TestClient, async_session: AsyncSession
):
    user_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    # Create chats, add user to chats
    chat_ids = [uuid.uuid4() for _ in range(3)]
    for chat_id in chat_ids:
        async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
        async_session.add(UserChatLink(chat_id=chat_id, user_id=user_id))
    await async_session.commit()

    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())

        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespGetJoinedChatList)
        if isinstance(srv_packet.data, SrvRespGetJoinedChatList):
            assert len(srv_packet.data.chats) == len(chat_ids)


def test_ws_chat_get_joined_chats__empty_list(client: TestClient):
    user_id = uuid.uuid4()
    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={user_id}") as websocket:
        websocket.send_text(client_packet.model_dump_json())

        resp_str = websocket.receive_text()

        srv_packet = ServerPacket.model_validate_json(resp_str)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespGetJoinedChatList)
        if isinstance(srv_packet.data, SrvRespGetJoinedChatList):
            assert len(srv_packet.data.chats) == 0


def test_ws_chat_get_joined_chats__error(client: TestClient):
    user_id = uuid.uuid4()
    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession

    raise_error = RepositoryError(detail="repo error")
    with patch.object(
        ChatManager,
        "get_joined_chat_list",
        new=Mock(side_effect=raise_error),
    ):
        with client.websocket_connect(f"/ws/chat?user_id={user_id}") as websocket:
            websocket.send_text(client_packet.model_dump_json())
            resp_str = websocket.receive_text()

            srv_packet = ServerPacket.model_validate_json(resp_str)
            assert srv_packet.request_packet_id == client_packet.id
            assert isinstance(srv_packet.data, SrvRespError)
            if isinstance(srv_packet.data, SrvRespError):
                assert srv_packet.data.error_data.error_code == raise_error.error_code
                assert srv_packet.data.error_data.detail == raise_error.detail
