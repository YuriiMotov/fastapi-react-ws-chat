import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.security import SecurityScopes
from freezegun import freeze_time

from backend.auth_setups import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    Scopes,
)
from backend.schemas.token_data import TokenData
from backend.schemas.tokens_response import TokensResponse
from backend.schemas.user import UserSchema
from backend.services.auth.abstract_auth import AbstractAuth
from backend.services.auth.auth_exc import (
    AuthBadCredentialsError,
    AuthBadRequestParametersError,
    AuthBadTokenError,
    AuthUnauthorizedError,
)


class AuthServiceTestBase:

    # Get token with pwd

    async def test_get_token_with_pwd__success(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[Scopes.chat_user.value],
        )
        assert isinstance(tokens, TokensResponse)
        assert len(tokens.access_token) > 0
        assert len(tokens.refresh_token) > 0
        assert tokens.token_type == "bearer"

    async def test_get_token_with_pwd__bad_credentials_username(
        self, auth_service: AbstractAuth
    ):
        with pytest.raises(AuthBadCredentialsError):
            await auth_service.get_token_with_pwd(
                user_name=uuid.uuid4().hex,
                password=uuid.uuid4().hex,
                requested_scopes=[Scopes.chat_user.value],
            )

    async def test_get_token_with_pwd__bad_credentials_password(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        with pytest.raises(AuthBadCredentialsError):
            await auth_service.get_token_with_pwd(
                user_name=user_data["name"],
                password=uuid.uuid4().hex,
                requested_scopes=[Scopes.chat_user.value],
            )

    async def test_get_token_with_pwd__bad_scopes(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        with pytest.raises(AuthBadRequestParametersError):
            await auth_service.get_token_with_pwd(
                user_name=user_data["name"],
                password=user_data["password"],
                requested_scopes=["root_access"],
            )

    # Get token with refresh token

    async def test_get_token_with_refresh_token__success(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[Scopes.chat_user.value],
        )
        assert isinstance(tokens, TokensResponse)
        refresh_token = tokens.refresh_token

        with freeze_time(datetime.now() + timedelta(seconds=1)):
            tokens_2 = await auth_service.get_token_with_refresh_token(
                refresh_token=refresh_token,
                requested_scopes=[Scopes.chat_user.value],
            )
        assert isinstance(tokens_2, TokensResponse)
        assert len(tokens_2.access_token) > 0
        assert len(tokens_2.refresh_token) > 0
        assert tokens_2.access_token != tokens.access_token
        assert tokens_2.refresh_token != tokens.refresh_token
        assert tokens_2.token_type == "bearer"

    async def test_get_token_with_refresh_token__bad_credentials_token_broken(
        self, auth_service: AbstractAuth
    ):
        with pytest.raises(AuthBadTokenError):
            await auth_service.get_token_with_refresh_token(
                refresh_token="bad_token..",
                requested_scopes=[Scopes.chat_user.value],
            )

    async def test_get_token_with_refresh_token__bad_credentials_token_outdated(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[Scopes.chat_user.value],
        )
        assert isinstance(tokens, TokensResponse)
        refresh_token = tokens.refresh_token
        with freeze_time(
            datetime.now() + REFRESH_TOKEN_EXPIRE_MINUTES + timedelta(minutes=1)
        ):
            with pytest.raises(AuthBadTokenError):
                await auth_service.get_token_with_refresh_token(
                    refresh_token=refresh_token,
                    requested_scopes=[Scopes.chat_user.value],
                )

    async def test_get_token_with_refresh__bad_scopes(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[Scopes.chat_user.value],
        )
        assert isinstance(tokens, TokensResponse)
        refresh_token = tokens.refresh_token
        with pytest.raises(AuthBadRequestParametersError):
            await auth_service.get_token_with_refresh_token(
                refresh_token=refresh_token,
                requested_scopes=["root_access"],
            )

    async def test_get_token_with_refresh__scopes_mismatch(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[],
        )
        assert isinstance(tokens, TokensResponse)
        refresh_token = tokens.refresh_token
        with pytest.raises(AuthBadRequestParametersError):
            await auth_service.get_token_with_refresh_token(
                refresh_token=refresh_token,
                requested_scopes=[Scopes.chat_user.value],
            )

    # Validate token

    async def test_vaidate_token__success(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[Scopes.chat_user.value],
        )
        assert isinstance(tokens, TokensResponse)
        access_token = tokens.access_token
        required_scopes = SecurityScopes([Scopes.chat_user.value])
        token_decoded = await auth_service.validate_token(
            token=access_token, required_scopes=required_scopes
        )
        assert isinstance(token_decoded, TokenData)
        assert (
            token_decoded.sub == user_data["id"]
        ), f"{token_decoded.sub} != {user_data['id']}"
        assert token_decoded.user_name == user_data["name"]

    async def test_vaidate_token__outdated(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[Scopes.chat_user.value],
        )
        assert isinstance(tokens, TokensResponse)
        access_token = tokens.access_token
        required_scopes = SecurityScopes([Scopes.chat_user.value])

        with freeze_time(
            datetime.now() + ACCESS_TOKEN_EXPIRE_MINUTES + timedelta(seconds=1)
        ):
            with pytest.raises(AuthBadTokenError):
                await auth_service.validate_token(
                    token=access_token, required_scopes=required_scopes
                )

    async def test_vaidate_token__wrong_scopes(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        tokens = await auth_service.get_token_with_pwd(
            user_name=user_data["name"],
            password=user_data["password"],
            requested_scopes=[Scopes.chat_user.value],
        )
        assert isinstance(tokens, TokensResponse)
        access_token = tokens.access_token
        required_scopes = SecurityScopes(["root_access"])

        with pytest.raises(AuthUnauthorizedError):
            await auth_service.validate_token(
                token=access_token, required_scopes=required_scopes
            )

    @pytest.mark.xfail(reason="Need to group settings into config object")
    async def test_vaidate_token__wrong_aud(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        with patch("backend.auth_setups.JWT_AUD", "another_aud"):
            tokens = await auth_service.get_token_with_pwd(
                user_name=user_data["name"],
                password=user_data["password"],
                requested_scopes=[Scopes.chat_user.value],
            )

        assert isinstance(tokens, TokensResponse)
        access_token = tokens.access_token
        required_scopes = SecurityScopes([Scopes.chat_user.value])

        with pytest.raises(AuthBadTokenError):
            await auth_service.validate_token(
                token=access_token, required_scopes=required_scopes
            )

    # Get current user

    async def test_current_user__success(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        token_decoded = TokenData(sub=user_data["id"], user_name=user_data["name"])
        user = await auth_service.get_current_user(access_token_decoded=token_decoded)
        assert isinstance(user, UserSchema)
        assert user.id.hex == user_data["id"]
        assert user.name == user_data["name"]

    async def test_current_user__wrong_sub(
        self, auth_service: AbstractAuth, user_data: dict[str, str]
    ):
        token_decoded = TokenData(sub=uuid.uuid4().hex, user_name=user_data["name"])
        with pytest.raises(AuthBadTokenError, match="Invalid user id"):
            await auth_service.get_current_user(access_token_decoded=token_decoded)
