import uuid

import pytest

from backend.auth_setups import Scopes
from backend.schemas.tokens_response import TokensResponse
from backend.services.auth.abstract_auth import AbstractAuth
from backend.services.auth.auth_exc import (
    AuthBadCredentialsError,
    AuthBadRequestParametersError,
)


class AuthServiceTestBase:

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
