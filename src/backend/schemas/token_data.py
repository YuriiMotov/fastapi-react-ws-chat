import uuid

from pydantic import BaseModel


class TokenData(BaseModel):
    user_uuid: uuid.UUID
    user_name: str
    scopes: list[str] = []
