from starlette.testclient import TestClient

from backend.auth_setups import (
    AUTH_ROUTER_PATH,
    TOKEN_PATH_WITH_PWD,
    TOKEN_PATH_WITH_REFRESH,
)

PWD_TOKEN_PATH = f"{AUTH_ROUTER_PATH}{TOKEN_PATH_WITH_PWD}"
REFRESH_TOKEN_PATH = f"{AUTH_ROUTER_PATH}{TOKEN_PATH_WITH_REFRESH}"


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
