from pydantic import BaseModel


class TokenData(BaseModel):
    sub: str
    user_name: str
    scopes: list[str] = []
