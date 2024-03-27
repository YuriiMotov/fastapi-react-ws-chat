import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class UserChatState(BaseModel):
    __tablename__ = "user_chat_state"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    chat_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chats.id"), primary_key=True)

    last_delivered: Mapped[int] = mapped_column(default=0)
    last_read: Mapped[int] = mapped_column(default=0)
