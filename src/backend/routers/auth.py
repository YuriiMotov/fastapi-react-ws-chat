from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from backend.auth_setups import auth_config
from backend.dependencies import get_auth_service
from backend.extended_security.oauth_refresh_scheme import OAuth2RefreshRequestForm
from backend.schemas.tokens_response import TokensResponse
from backend.schemas.user import UserCreateSchema, UserSchema
from backend.services.auth.abstract_auth import AbstractAuth
from backend.services.auth.auth_exc import (
    AuthBadRequestParametersError,
    AuthUnauthorizedError,
)

auth_router = APIRouter(prefix=auth_config.AUTH_ROUTER_PATH)


@auth_router.post("/register", status_code=201)
async def register(
    auth_service: Annotated[AbstractAuth, Depends(get_auth_service)],
    user_data: UserCreateSchema,
) -> UserSchema:
    try:
        return await auth_service.register_user(user_data=user_data)
    except AuthBadRequestParametersError as exc:
        raise HTTPException(status_code=400, detail=f"{exc}: {exc.detail}")


@auth_router.post(auth_config.TOKEN_PATH_WITH_PWD)
async def get_token_with_pwd(
    auth_service: Annotated[AbstractAuth, Depends(get_auth_service)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokensResponse:
    try:
        return await auth_service.get_token_with_pwd(
            form_data.username, form_data.password, form_data.scopes
        )
    except AuthBadRequestParametersError as exc:
        raise HTTPException(status_code=400, detail=exc.detail)
    except AuthUnauthorizedError as exc:
        raise HTTPException(status_code=403, detail=exc.detail, headers=exc.headers)


@auth_router.post(auth_config.TOKEN_PATH_WITH_REFRESH)
async def get_token_with_refresh_token(
    auth_service: Annotated[AbstractAuth, Depends(get_auth_service)],
    form_data: Annotated[OAuth2RefreshRequestForm, Depends()],
) -> TokensResponse:
    try:
        return await auth_service.get_token_with_refresh_token(
            form_data.refresh_token, form_data.scopes
        )
    except AuthBadRequestParametersError as exc:
        raise HTTPException(status_code=400, detail=exc.detail)
    except AuthUnauthorizedError as exc:
        raise HTTPException(status_code=403, detail=exc.detail, headers=exc.headers)
