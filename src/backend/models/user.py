import uuid

from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        nullable=False,
    )
    name: Mapped[str]
    hashed_password: Mapped[str] = mapped_column(default="")  # Default val is temporary
    scope: Mapped[str] = mapped_column(default="")
