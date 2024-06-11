import uuid

from pydantic import Field

from backend.schemas.base import BaseSchema


class UserBaseSchema(BaseSchema):
    name: str


class UserSchema(UserBaseSchema):
    id: uuid.UUID


class UserCreateSchema(UserBaseSchema):
    password: str = Field(min_length=6)
