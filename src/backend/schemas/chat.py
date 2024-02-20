import uuid

from .base import BaseSchema


class ChatSchema(BaseSchema):
    id: uuid.UUID
    title: str
    owner_id: uuid.UUID


class ChatSchemaCreate(ChatSchema):
    pass


class ChatExtSchema(ChatSchema):
    last_message_text: str | None
    members_count: int
    pass
