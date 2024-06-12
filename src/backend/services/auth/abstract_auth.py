from abc import ABC, abstractmethod
from typing import Literal, TypeAlias

from fastapi.security import SecurityScopes

from backend.auth_setups import Scopes
from backend.schemas.token_data import TokenData
from backend.schemas.tokens_response import TokensResponse
from backend.schemas.user import UserCreateSchema, UserSchema

DEFAULT_SCOPES = [Scopes.chat_user]

TokenType: TypeAlias = Literal["access", "refresh"]


class AbstractAuth(ABC):

    @abstractmethod
    async def register_user(
        self,
        user_data: UserCreateSchema,
    ):
        raise NotImplementedError()

    @abstractmethod
    async def get_token_with_pwd(
        self, user_name: str, password: str, requested_scopes: list[str]
    ) -> TokensResponse:
        raise NotImplementedError()

    @abstractmethod
    async def get_token_with_refresh_token(
        self, refresh_token: str, requested_scopes: list[str]
    ) -> TokensResponse:
        raise NotImplementedError()

    @abstractmethod
    async def validate_token(
        self, token: str, token_type: TokenType, required_scopes: SecurityScopes | None
    ) -> TokenData:
        raise NotImplementedError()

    @abstractmethod
    async def get_current_user(self, access_token_decoded: TokenData) -> UserSchema:
        raise NotImplementedError()
