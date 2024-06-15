import uuid
from typing import Annotated
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.testclient import TestClient, WebSocketTestSession

from backend.auth_setups import (
    AUTH_ROUTER_PATH,
    TOKEN_PATH_WITH_PWD,
    TOKEN_PATH_WITH_REFRESH,
)
from backend.dependencies import get_current_user, sqla_sessionmaker_dep
from backend.routers.auth import auth_router
from backend.schemas.user import UserCreateSchema, UserSchema

PWD_TOKEN_PATH = f"{AUTH_ROUTER_PATH}{TOKEN_PATH_WITH_PWD}"
REFRESH_TOKEN_PATH = f"{AUTH_ROUTER_PATH}{TOKEN_PATH_WITH_REFRESH}"
REGISTER_PATH = f"{AUTH_ROUTER_PATH}/register"

# Get token pwd


async def test_get_token_pwd_endpoint__success(
    client: TestClient, registered_user_data: dict[str, str]
):
    user = registered_user_data
    res = client.post(
        PWD_TOKEN_PATH,
        data={
            "grant_type": "password",
            "username": user["name"],
            "password": user["password"],
            "scope": user["scope"],
        },
    )
    assert res.status_code == 200, res.json()
    tokens = res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert "token_type" in tokens


async def test_get_token_pwd_endpoint__wrong_password(
    client: TestClient, registered_user_data: dict[str, str]
):
    user = registered_user_data
    res = client.post(
        PWD_TOKEN_PATH,
        data={
            "grant_type": "password",
            "username": user["name"],
            "password": "wrong_pass",
            "scope": user["scope"],
        },
    )
    assert res.status_code == 400, res.json()
    json_data = res.json()
    assert json_data["detail"] == "Incorrect username or password"


async def test_get_token_pwd_endpoint__wrong_scope(
    client: TestClient, registered_user_data: dict[str, str]
):
    user = registered_user_data
    res = client.post(
        PWD_TOKEN_PATH,
        data={
            "grant_type": "password",
            "username": user["name"],
            "password": user["password"],
            "scope": "root_access",
        },
    )
    assert res.status_code == 400, res.json()
    json_data = res.json()
    assert json_data["detail"] == "Incorrect requested scopes"


# Get token refresh


async def test_get_token_refresh_token_endpoint__success(
    client: TestClient, registered_user_data: dict[str, str]
):
    user = registered_user_data
    res = client.post(
        PWD_TOKEN_PATH,
        data={
            "grant_type": "password",
            "username": user["name"],
            "password": user["password"],
            "scope": user["scope"],
        },
    )
    assert res.status_code == 200, res.json()
    tokens = res.json()

    res2 = client.post(
        REFRESH_TOKEN_PATH,
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "scope": user["scope"],
        },
    )
    assert res2.status_code == 200, res2.json()
    tokens2 = res2.json()
    assert "access_token" in tokens2
    assert "refresh_token" in tokens2
    assert "token_type" in tokens2


async def test_get_token_refresh_token_endpoint__wrong_token(
    client: TestClient, registered_user_data: dict[str, str]
):
    user = registered_user_data
    res = client.post(
        REFRESH_TOKEN_PATH,
        data={
            "grant_type": "refresh_token",
            "refresh_token": "wrong_token",
            "scope": user["scope"],
        },
    )
    assert res.status_code == 400, res.json()
    json_data = res.json()
    assert json_data["detail"] == "Invalid token"


# Protect endpoints (http and websocket)


@pytest.fixture()
def protected_app_client(async_session_maker: async_sessionmaker):
    app_protected = FastAPI()
    app_protected.include_router(auth_router)

    @app_protected.get("/protected_get")
    def protected_get(user: Annotated[UserSchema, Depends(get_current_user)]):
        return user.id.hex

    @app_protected.websocket("/protected_ws")
    async def protected_ws(
        websocket: WebSocket,
        user: Annotated[UserSchema, Depends(get_current_user)],
    ):
        await websocket.accept()
        try:
            await websocket.send_text(user.id.hex)
            await websocket.receive_text()
        except WebSocketDisconnect:
            pass

    def get_sessionmaker():
        return async_session_maker

    app_protected.dependency_overrides[sqla_sessionmaker_dep] = get_sessionmaker

    with TestClient(app_protected) as client:
        yield client


@pytest.fixture()
def protected_app_access_token(
    protected_app_client: TestClient, registered_user_data: dict[str, str]
):
    res = protected_app_client.post(
        PWD_TOKEN_PATH,
        data={
            "grant_type": "password",
            "username": registered_user_data["name"],
            "password": registered_user_data["password"],
            "scope": registered_user_data["scope"],
        },
    )
    assert res.status_code == 200, res.json()
    tokens = res.json()
    return tokens["access_token"]


def test_protected_get__success(
    protected_app_client: TestClient,
    registered_user_data: dict[str, str],
    protected_app_access_token: str,
):
    res = protected_app_client.get(
        "/protected_get",
        headers={"Authorization": f"Bearer {protected_app_access_token}"},
    )
    assert res.status_code == 200
    assert res.json() == registered_user_data["id"]


def test_protected_get__unauthorized_missed_token(
    protected_app_client: TestClient,
):
    res = protected_app_client.get(
        "/protected_get",
    )
    assert res.status_code == 401, res.json()
    assert res.headers["www-authenticate"].lower() == "bearer"


def test_protected_get__unauthorized_invalid_token(
    protected_app_client: TestClient,
):
    res = protected_app_client.get(
        "/protected_get",
        headers={"Authorization": "Bearer WRONG_TOKEN"},
    )
    assert res.status_code == 403, res.json()
    assert res.headers["www-authenticate"].lower() == "bearer"


def test_protected_ws__success(
    protected_app_client: TestClient,
    registered_user_data: dict[str, str],
    protected_app_access_token: str,
):
    protected_app_client.headers["Authorization"] = (
        f"Bearer {protected_app_access_token}"
    )
    ws_connection: WebSocketTestSession
    with protected_app_client.websocket_connect("/protected_ws") as ws_connection:
        user_id = ws_connection.receive_text()
        assert user_id == registered_user_data["id"]


def test_protected_ws__unauthorized_missed_token(
    protected_app_client: TestClient,
):
    ws_connection: WebSocketTestSession

    with pytest.raises(WebSocketDisconnect):
        with protected_app_client.websocket_connect("/protected_ws") as ws_connection:
            ws_connection.receive_text()


def test_protected_ws__unauthorized_invalid_token(
    protected_app_client: TestClient,
):
    protected_app_client.headers["Authorization"] = "Bearer WRONG_TOKEN"
    ws_connection: WebSocketTestSession

    with pytest.raises(WebSocketDisconnect):
        with protected_app_client.websocket_connect("/protected_ws") as ws_connection:
            ws_connection.receive_text()


# Register user


def test_register_user__success(client: TestClient):
    user_data = UserCreateSchema(
        name=f"user_{uuid.uuid4()}", password=uuid.uuid4().hex[:8]
    )
    resp = client.post(REGISTER_PATH, json=user_data.model_dump())
    assert resp.status_code == 201, resp.json()
    created_user = UserSchema.model_validate(resp.json())
    assert isinstance(created_user, UserSchema)
    assert created_user.name == user_data.name
    assert isinstance(created_user.id, uuid.UUID)


def test_register_user__error_diplicated_name(
    client: TestClient, registered_user_data: dict[str, str]
):
    user_data = UserCreateSchema(
        name=registered_user_data["name"], password=uuid.uuid4().hex[:8]
    )
    resp = client.post(REGISTER_PATH, json=user_data.model_dump())
    assert resp.status_code == 400, resp.json()
    error = resp.json()
    assert "Duplicated user name" in error["detail"]


def test_register_user__error_diplicated_uid(
    client: TestClient, registered_user_data: dict[str, str]
):
    user_data = UserCreateSchema(
        name=f"user_{uuid.uuid4()}", password=uuid.uuid4().hex[:8]
    )
    uid = uuid.UUID(registered_user_data["id"])
    with patch.object(uuid, "uuid4", return_value=uid):
        resp = client.post(REGISTER_PATH, json=user_data.model_dump())
        assert resp.status_code == 500, resp.json()
