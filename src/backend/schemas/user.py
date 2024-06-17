import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from backend.schemas.base import BaseSchema


class UserBaseSchema(BaseSchema):
    name: str
    updated_at: Optional[datetime] = None


class UserSchema(UserBaseSchema):
    id: uuid.UUID


class UserCreateSchema(UserBaseSchema):
    password: str = Field(min_length=6)
