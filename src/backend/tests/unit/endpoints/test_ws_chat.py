import random
import uuid

from starlette.testclient import TestClient, WebSocketTestSession

from backend.schemas.client_packet import ClientPacket, CMDGetJoinedChats
from backend.schemas.server_packet import ServerPacket, SrvRespGetJoinedChatList


def test_ws_chat_connect(client: TestClient):
    user_id = uuid.uuid4()
    websocket: WebSocketTestSession
    with client.websocket_connect(
        f"/ws/chat?user_id={user_id}"
    ) as websocket:  # noqa: F841
        pass


def test_ws_chat_get_chats__empty_list(client: TestClient):
    user_id = uuid.uuid4()
    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    websocket: WebSocketTestSession
    with client.websocket_connect(f"/ws/chat?user_id={user_id}") as websocket:
        websocket.send_json(client_packet.model_dump())

        resp = websocket.receive_json()

        srv_packet = ServerPacket.model_validate(resp)
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespGetJoinedChatList)
        if isinstance(srv_packet.data, SrvRespGetJoinedChatList):
            assert len(srv_packet.data.chats) == 0
