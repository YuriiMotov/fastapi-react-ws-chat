from abc import ABC, abstractmethod

from fastapi.security import SecurityScopes

from backend.schemas.token_data import TokenData
from backend.schemas.tokens_response import TokensResponse
from backend.schemas.user import UserSchema


class AbstractAuth(ABC):

    @abstractmethod
    async def register_user(
        self,
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
        self, token: str, required_scopes: SecurityScopes | None
    ) -> TokenData:
        raise NotImplementedError()

    @abstractmethod
    async def get_current_user(self, access_token_decoded: TokenData) -> UserSchema:
        raise NotImplementedError()
