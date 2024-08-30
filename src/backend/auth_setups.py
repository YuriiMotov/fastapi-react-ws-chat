import logging
from datetime import timedelta
from enum import Enum

from passlib.context import CryptContext

from backend.extended_security.auth2_password_bearer import OAuth2PasswordBearerWsHttp

logger = logging.getLogger("passlib")
logger.setLevel(logging.ERROR)


class Scopes(str, Enum):
    chat_user: str = "chat_user"


class AuthConfig:
    # Сonfigure this according to how you mount the router
    AUTH_ROUTER_PATH = "/auth"

    TOKEN_PATH_WITH_PWD = "/token"

    TOKEN_PATH_WITH_REFRESH = f"{TOKEN_PATH_WITH_PWD}-refresh"

    SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_TIMEDELTA = timedelta(minutes=2)
    PWD_HASH_ROUNDS = 8
    REFRESH_TOKEN_EXPIRE_TIMEDELTA = timedelta(minutes=60 * 24 * 2)

    JWT_AUD = "ws-chat"

    pwd_context = CryptContext(
        schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=PWD_HASH_ROUNDS
    )

    app_scopes = {
        Scopes.chat_user.value: "WS chat user",
    }

    oauth2_scheme = OAuth2PasswordBearerWsHttp(
        tokenUrl=f"{AUTH_ROUTER_PATH}{TOKEN_PATH_WITH_PWD}", scopes=app_scopes
    )


auth_config = AuthConfig()
