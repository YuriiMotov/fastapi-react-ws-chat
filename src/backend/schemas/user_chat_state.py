import uuid

from .base import BaseSchema


class UserChatStateSchema(BaseSchema):
    user_id: uuid.UUID
    chat_id: uuid.UUID
    last_delivered: int
    last_read: int
