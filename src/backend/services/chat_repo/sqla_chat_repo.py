import uuid
from contextlib import contextmanager

from pydantic import TypeAdapter
from sqlalchemy import and_, delete, insert, select
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat, ChatExt
from backend.models.chat_message import ChatMessage, ChatNotification, ChatUserMessage
from backend.models.user_chat_link import UserChatLink
from backend.models.user_chat_state import UserChatState
from backend.schemas.chat import ChatExtSchema, ChatSchema
from backend.schemas.chat_message import (
    AnnotatedChatMessageAny,
    ChatMessageAny,
    ChatNotificationCreateSchema,
    ChatNotificationSchema,
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from backend.schemas.user_chat_state import UserChatStateSchema
from backend.services.chat_repo.abstract_chat_repo import (
    MAX_MESSAGE_COUNT_PER_PAGE,
    AbstractChatRepo,
)
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

    async def get_chat(self, chat_id: uuid.UUID) -> ChatSchema | None:
        with sqla_exceptions_to_repo_exc():
            chat = await self._session.get(Chat, chat_id)
            if chat is not None:
                return ChatSchema.model_validate(chat)
            return None

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

    async def get_joined_chat_list(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int | None = None,
        chat_id_list: list[uuid.UUID] | None = None,
    ) -> list[ChatExtSchema]:
        chat_ids_st = (
            select(UserChatLink.chat_id)
            .where(UserChatLink.user_id == user_id)
            .offset(offset)
        )
        if chat_id_list:
            chat_ids_st = chat_ids_st.where(UserChatLink.chat_id.in_(chat_id_list))
        if limit is not None:
            chat_ids_st = chat_ids_st.limit(limit)

        chats_st = select(ChatExt).where(ChatExt.id.in_(chat_ids_st))
        with sqla_exceptions_to_repo_exc():
            chats = await self._session.scalars(chats_st)

        return [ChatExtSchema.model_validate(chat) for chat in chats]

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

    async def edit_message(
        self, message_id: int, sender_id_filter: uuid.UUID, text: str
    ) -> ChatUserMessageSchema:
        with sqla_exceptions_to_repo_exc():
            message = await self._session.get(ChatUserMessage, message_id)
            if message is None:
                raise ChatRepoRequestError(detail=f"Message with id={id} doesnt exist")
            if message.sender_id != sender_id_filter:
                raise ChatRepoRequestError(
                    detail=f"Wrong sender_id for message with id={id}"
                )
            message.text = text
            return ChatUserMessageSchema.model_validate(message)

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

    async def get_message_list(
        self,
        chat_id: uuid.UUID,
        start_id: int = -1,
        order_desc: bool = True,
        limit: int = MAX_MESSAGE_COUNT_PER_PAGE,
    ) -> list[ChatMessageAny]:
        with sqla_exceptions_to_repo_exc():
            st = select(ChatMessage).where(ChatMessage.chat_id == chat_id)
            if order_desc:
                if start_id > 0:
                    st = st.where(ChatMessage.id < start_id)
                st = st.order_by(ChatMessage.id.desc())
            else:
                if start_id > 0:
                    st = st.where(ChatMessage.id > start_id)
                st = st.order_by(ChatMessage.id)
            st = st.limit(limit)
            res = await self._session.scalars(st)
            message_adapter: TypeAdapter[ChatMessageAny] = TypeAdapter(
                AnnotatedChatMessageAny  # type: ignore
            )

            return [message_adapter.validate_python(message) for message in res]

    async def get_user_chat_state(
        self,
        user_id: uuid.UUID,
    ) -> list[UserChatStateSchema]:
        with sqla_exceptions_to_repo_exc():
            res = await self._session.scalars(
                select(UserChatState).where(UserChatState.user_id == user_id)
            )
            return [UserChatStateSchema.model_validate(state) for state in res.all()]

    async def update_user_chat_state_from_dict(
        self, user_id: uuid.UUID, user_chat_state_dict: dict[uuid.UUID, dict[str, int]]
    ):
        await self._session.execute(
            delete(UserChatState).where(
                and_(
                    UserChatState.chat_id.in_(user_chat_state_dict.keys()),
                    UserChatState.user_id == user_id,
                )
            )
        )
        insert_data = [
            {"chat_id": chat_id, "user_id": user_id, **state_item}
            for (chat_id, state_item) in user_chat_state_dict.items()
        ]
        with sqla_exceptions_to_repo_exc():
            await self._session.execute(insert(UserChatState), insert_data)
