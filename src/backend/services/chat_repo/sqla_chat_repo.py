import uuid
from contextlib import contextmanager

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatNotification, ChatUserMessage
from backend.models.user_chat_link import UserChatLink
from backend.schemas.chat import ChatSchema
from backend.schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatNotificationSchema,
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from backend.services.chat_repo.abstract_chat_repo import AbstractChatRepo
from backend.services.chat_repo.chat_repo_exc import (
    ChatRepoDatabaseError,
    ChatRepoException,
    ChatRepoRequestError,
)


@contextmanager
def sqla_exceptions_to_repo_exc(*args, **kwds):
    """
    Intercept SQLAlchemy exceptions and raise ChatRepo exceptions
    """
    try:
        yield
    except (IntegrityError,) as exc:
        raise ChatRepoRequestError(detail=str(exc))
    except OperationalError as exc:
        raise ChatRepoDatabaseError(detail=str(exc))
    except SQLAlchemyError as exc:
        raise ChatRepoDatabaseError(detail=str(exc))


class SQLAlchemyChatRepo(AbstractChatRepo):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_chat(self, chat: ChatSchema) -> ChatSchema:
        with sqla_exceptions_to_repo_exc():
            chat_db = await self._session.scalar(
                insert(Chat).returning(Chat), params=chat.model_dump()
            )
        return ChatSchema.model_validate(chat_db)

    async def get_owned_chats(
        self, owner_id: uuid.UUID, offset: int = 0, limit: int | None = None
    ) -> list[ChatSchema]:
        st = select(Chat).where(Chat.owner_id == owner_id).offset(offset)
        if limit is not None:
            st = st.limit(limit)
        with sqla_exceptions_to_repo_exc():
            res = await self._session.scalars(st)
        return [ChatSchema.model_validate(chat) for chat in res]

    async def get_joined_chat_ids(
        self, user_id: uuid.UUID, offset: int = 0, limit: int | None = None
    ) -> list[uuid.UUID]:
        st = (
            select(UserChatLink.chat_id)
            .where(UserChatLink.user_id == user_id)
            .offset(offset)
        )
        if limit is not None:
            st = st.limit(limit)
        with sqla_exceptions_to_repo_exc():
            res = await self._session.scalars(st)
        return list(res)

    async def add_user_to_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> None:
        with sqla_exceptions_to_repo_exc():
            await self._session.execute(
                insert(UserChatLink), {"user_id": user_id, "chat_id": chat_id}
            )

    async def add_message(
        self, message: ChatUserMessageCreateSchema
    ) -> ChatUserMessageSchema:
        with sqla_exceptions_to_repo_exc():
            message_in_db = await self._session.scalar(
                insert(ChatUserMessage).returning(ChatUserMessage),
                message.model_dump(exclude_unset=True),
            )
        if message_in_db:
            return ChatUserMessageSchema.model_validate(message_in_db)
        else:
            raise ChatRepoException()

    async def add_notification(
        self, notification: ChatNotificationCreateSchema
    ) -> ChatNotificationSchema:
        with sqla_exceptions_to_repo_exc():
            notification_in_db = await self._session.scalar(
                insert(ChatNotification).returning(ChatNotification),
                notification.model_dump(exclude_unset=True),
            )
        if notification_in_db:
            return ChatNotificationSchema.model_validate(notification_in_db)
        else:
            raise ChatRepoException()
