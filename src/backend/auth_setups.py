from datetime import timedelta
from enum import Enum

from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

# Сonfigure this according to how you mount the router
ROUTER_PATH = "/auth"

TOKEN_PATH_BASE = f"{ROUTER_PATH}/token"
TOKEN_PATH_WITH_PWD = TOKEN_PATH_BASE
TOKEN_PATH_WITH_REFRESH = f"{TOKEN_PATH_BASE}-refresh"
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = timedelta(minutes=2)
REFRESH_TOKEN_EXPIRE_MINUTES = timedelta(minutes=60 * 24 * 2)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Scopes(str, Enum):
    chat_user: str = "chat_user"


app_scopes = {
    Scopes.chat_user.value: "WS chat user",
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=TOKEN_PATH_WITH_PWD, scopes=app_scopes)
