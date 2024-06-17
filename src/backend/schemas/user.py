import uuid
from datetime import datetime

from pydantic import Field

from backend.schemas.base import BaseSchema


class UserBaseSchema(BaseSchema):
    name: str


class UserSchema(UserBaseSchema):
    id: uuid.UUID


class UserSchemaExt(UserSchema):
    updated_at: datetime = Field(default_factory=datetime.now)


class UserCreateSchema(UserBaseSchema):
    password: str = Field(min_length=6)
