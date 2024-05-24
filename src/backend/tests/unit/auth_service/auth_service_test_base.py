import uuid
from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from backend.auth_setups import REFRESH_TOKEN_EXPIRE_MINUTES, Scopes
from backend.schemas.tokens_response import TokensResponse
from backend.services.auth.abstract_auth import AbstractAuth
from backend.services.auth.auth_exc import (
    AuthBadCredentialsError,
    AuthBadRequestParametersError,
    AuthBadTokenError,
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
