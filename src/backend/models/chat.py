import uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class Chat(BaseModel):
    __tablename__ = "chats"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        nullable=False,
    )
    title: Mapped[str]
    owner_id: Mapped[uuid.UUID]
