import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class ChatMessage(BaseModel):
    __tablename__ = "chat_messages"
    __mapper_args__ = {
        "polymorphic_on": "is_notification",
        "polymorphic_identity": None,
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    is_notification: Mapped[bool]
    chat_id: Mapped[uuid.UUID]
    text: Mapped[str]
    dt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChatUserMessage(ChatMessage):
    __tablename__ = "chat_user_messages"
    __mapper_args__ = {
        "polymorphic_identity": False,
    }

    id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id"), primary_key=True)
    sender_id: Mapped[uuid.UUID]

    def __init__(self, chat_id: uuid.UUID, text: str, sender_id: uuid.UUID):
        self.chat_id = chat_id
        self.text = text
        self.sender_id = sender_id


class ChatNotification(ChatMessage):
    __tablename__ = "chat_notifications"
    __mapper_args__ = {
        "polymorphic_identity": True,
    }

    id: Mapped[int] = mapped_column(ForeignKey("chat_messages.id"), primary_key=True)
    params: Mapped[str]

    def __init__(self, chat_id: uuid.UUID, text: str, params: str):
        self.chat_id = chat_id
        self.text = text
        self.params = params
