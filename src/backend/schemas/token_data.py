from pydantic import BaseModel


class TokenData(BaseModel):
    user_uuid: str
    user_name: str
    scopes: list[str] = []
