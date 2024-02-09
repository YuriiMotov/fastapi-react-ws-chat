import uuid

from models.chat import Chat
from models.chat_message import ChatNotification, ChatUserMessage
from models.user_chat_link import UserChatLink
from schemas.chat import ChatSchema
from schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatNotificationSchema,
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from services.chat_repo.abstract_chat_repo import (
    PAGE_LIMIT_DEFAULT,
    AbstractChatRepo,
    ChatRepoException,
)
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyChatRepo(AbstractChatRepo):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_chat(self, chat: ChatSchema) -> ChatSchema:
        chat_db = await self._session.scalar(
            insert(Chat).returning(Chat), params=chat.model_dump()
        )
        return ChatSchema.model_validate(chat_db)

    async def get_chats(
        self, owner_id: uuid.UUID, offset: int = 0, limit: int = PAGE_LIMIT_DEFAULT
    ) -> list[ChatSchema]:
        st = select(Chat).where(Chat.owner_id == owner_id).offset(offset).limit(limit)
        res = await self._session.scalars(st)
        return [ChatSchema.model_validate(chat) for chat in res]

    async def add_user_to_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID):
        await self._session.execute(
            insert(UserChatLink), {"user_id": user_id, "chat_id": chat_id}
        )

    async def add_message(
        self, message: ChatUserMessageCreateSchema
    ) -> ChatUserMessageSchema:
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

        notification_in_db = await self._session.scalar(
            insert(ChatNotification).returning(ChatNotification),
            notification.model_dump(exclude_unset=True),
        )
        if notification_in_db:
            return ChatNotificationSchema.model_validate(notification_in_db)
        else:
            raise ChatRepoException()
