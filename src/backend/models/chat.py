import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column

from backend.models.chat_message import ChatUserMessage
from backend.models.user_chat_link import UserChatLink

from .base import BaseModel


class Chat(BaseModel):
    __tablename__ = "chats"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        nullable=False,
    )
    title: Mapped[str]
    owner_id: Mapped[uuid.UUID]


class ChatExt(Chat):
    last_message_text: Mapped[str] = column_property(
        select(ChatUserMessage.text)
        .where(ChatUserMessage.chat_id == Chat.id)
        .order_by(ChatUserMessage.id.desc())
        .limit(1)
        .correlate_except(ChatUserMessage)
        .scalar_subquery()
    )
    members_count: Mapped[int] = column_property(
        select(func.count(UserChatLink.user_id))
        .where(UserChatLink.chat_id == Chat.id)
        .correlate_except(UserChatLink)
        .scalar_subquery()
    )
    pass
