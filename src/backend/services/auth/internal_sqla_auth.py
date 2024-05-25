import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import jwt
from fastapi.security import SecurityScopes
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth_setups import (
    ACCESS_TOKEN_EXPIRE_TIMEDELTA,
    ALGORITHM,
    JWT_AUD,
    REFRESH_TOKEN_EXPIRE_TIMEDELTA,
    SECRET_KEY,
    pwd_context,
)
from backend.models.user import User
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


class InternalSQLAAuth(AbstractAuth):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_user(self):
        raise NotImplementedError()

    async def get_token_with_pwd(
        self, user_name: str, password: str, requested_scopes: list[str]
    ) -> TokensResponse:
        user = await self.session.scalar(select(User).where(User.name == user_name))
        if not user:
            raise AuthBadCredentialsError(detail="Incorrect username or password")
        is_password_correct = pwd_context.verify(password, user.hashed_password)
        if not is_password_correct:
            raise AuthBadCredentialsError(detail="Incorrect username or password")
        user_scopes = user.scope.split(" ")
        if not set(requested_scopes).issubset(set(user_scopes)):
            raise AuthBadRequestParametersError(detail="Incorrect requested scopes")

        tokens = self._create_token_pair(
            user_uuid=user.id.hex,
            user_name=user.name,
            requested_scopes=requested_scopes,
        )
        return tokens

    async def get_token_with_refresh_token(
        self, refresh_token: str, requested_scopes: list[str]
    ) -> TokensResponse:
        refresh_token_decoded = await self.validate_token(
            token=refresh_token, required_scopes=None
        )
        user = await self.session.get(User, uuid.UUID(refresh_token_decoded.sub))
        if not user:
            raise AuthBadCredentialsError(detail="Incorrect refresh token data")
        user_scopes = user.scope.split(" ")
        if not set(requested_scopes).issubset(
            set(user_scopes) & set(refresh_token_decoded.scopes)
        ):
            raise AuthBadRequestParametersError(detail="Incorrect requested scopes")

        tokens = self._create_token_pair(
            user_uuid=user.id.hex,
            user_name=user.name,
            requested_scopes=requested_scopes,
        )
        return tokens

    async def validate_token(
        self, token: str, required_scopes: SecurityScopes | None
    ) -> TokenData:
        authenticate_value = (
            f'Bearer scope="{required_scopes.scope_str}"'
            if (required_scopes and required_scopes.scopes)
            else "Bearer"
        )
        try:
            payload = cast(
                dict[str, Any],
                jwt.decode(
                    jwt=token,
                    audience=JWT_AUD,
                    key=SECRET_KEY,
                    algorithms=[ALGORITHM],
                    options={"require": ["exp", "aud", "sub"]},
                ),
            )
            sub: str = cast(str, payload.get("sub", ""))
            user_name: str = cast(str, payload.get("user_name", ""))
            token_scopes = cast(list[str], payload.get("scopes", []))
            token_data = TokenData.model_validate(
                {"scopes": token_scopes, "sub": sub, "user_name": user_name}
            )
        except (jwt.InvalidTokenError, ValidationError):
            raise AuthBadTokenError(
                detail="Invalid token", headers={"WWW-Authenticate": authenticate_value}
            )
        if required_scopes and (not set(required_scopes.scopes).issubset(token_scopes)):
            raise AuthUnauthorizedError(
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
        return token_data

    async def get_current_user(self, access_token_decoded: TokenData) -> UserSchema:
        user = await self.session.get(User, uuid.UUID(access_token_decoded.sub))
        if not user:
            raise AuthBadTokenError(detail="Invalid user id")
        return UserSchema.model_validate(user)

    # Private methods

    def _create_token(self, data: TokenData, expires_delta: timedelta):
        to_encode = data.model_dump()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire, "aud": JWT_AUD})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def _create_token_pair(
        self, user_uuid: str, user_name: str, requested_scopes: list[str]
    ) -> TokensResponse:
        token_data = TokenData(
            sub=user_uuid, user_name=user_name, scopes=requested_scopes
        )
        access_token = self._create_token(token_data, ACCESS_TOKEN_EXPIRE_TIMEDELTA)
        refresh_token = self._create_token(token_data, REFRESH_TOKEN_EXPIRE_TIMEDELTA)
        return TokensResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
