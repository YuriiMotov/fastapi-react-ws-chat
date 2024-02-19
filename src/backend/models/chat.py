import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Mapped, column_property, mapped_column

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
    # last_message_text: Mapped[str] = query_expression()
    members_count: Mapped[int] = column_property(
        select(func.count(UserChatLink.user_id))
        .where(Chat.id == UserChatLink.chat_id)
        .correlate_except(Chat)
        .scalar_subquery()
    )
    pass
