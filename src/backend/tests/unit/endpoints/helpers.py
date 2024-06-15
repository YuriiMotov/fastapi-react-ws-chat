from datetime import datetime, timezone
from typing import Any

import jwt
from starlette.testclient import TestClient, WebSocketTestSession

from backend.auth_setups import (
    ACCESS_TOKEN_EXPIRE_TIMEDELTA,
    ALGORITHM,
    JWT_AUD,
    SECRET_KEY,
)
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


def create_access_token(
    user_data: dict[str, str],
    scopes: list[str],
):
    to_encode: dict[str, Any] = {
        "sub": user_data["id"],
        "user_name": user_data["name"],
        "scopes": scopes,
    }
    expire = datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE_TIMEDELTA
    to_encode.update({"exp": expire, "aud": JWT_AUD, "token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
