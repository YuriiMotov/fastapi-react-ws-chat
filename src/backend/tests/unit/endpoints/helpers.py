from starlette.testclient import TestClient, WebSocketTestSession

from backend.schemas.client_packet import ClientPacket
from backend.schemas.server_packet import ServerPacket


def perform_request(
    websocket: WebSocketTestSession, client_packet: ClientPacket | None
) -> ServerPacket:
    if client_packet is not None:
        websocket.send_text(client_packet.model_dump_json())
    resp_str = websocket.receive_text()
    return ServerPacket.model_validate_json(resp_str)


def connect_and_perform_request(
    client: TestClient, url: str, client_packet: ClientPacket | None
) -> ServerPacket:
    websocket: WebSocketTestSession
    with client.websocket_connect(url) as websocket:
        return perform_request(websocket, client_packet)
