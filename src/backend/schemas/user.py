import uuid

from backend.schemas.base import BaseSchema


class UserSchema(BaseSchema):
    id: uuid.UUID
    name: str
