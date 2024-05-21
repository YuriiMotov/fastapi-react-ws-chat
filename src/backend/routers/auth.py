from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from backend.auth_setups import TOKEN_PATH_WITH_PWD, TOKEN_PATH_WITH_REFRESH
from backend.dependencies import get_auth_service
from backend.routers.oauth_refresh_scheme import OAuth2RefreshRequestForm
from backend.schemas.tokens_response import TokensResponse
from backend.services.auth.abstract_auth import AbstractAuth

router = APIRouter()


@router.post("/register")
async def register(
    auth_service: Annotated[AbstractAuth, Depends(get_auth_service)],
):
    pass


@router.get(f"/{TOKEN_PATH_WITH_PWD}")
async def get_token_with_pwd(
    auth_service: Annotated[AbstractAuth, Depends(get_auth_service)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokensResponse:
    return await auth_service.get_token_with_pwd(
        form_data.username, form_data.password, form_data.scopes
    )


@router.get(f"/{TOKEN_PATH_WITH_REFRESH}")
async def get_token_with_refresh_token(
    auth_service: Annotated[AbstractAuth, Depends(get_auth_service)],
    form_data: Annotated[OAuth2RefreshRequestForm, Depends()],
) -> TokensResponse:
    return await auth_service.get_token_with_refresh_token(
        form_data.refresh_token, form_data.scopes
    )
