import uuid
from services.chat_manager.chat_manager_exc import UnauthorizedAction
from services.uow.abstract_uow import AbstractUnitOfWork
from schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
)

USER_JOINED_CHAT_NOTIFICATION = "USER_JOINED_CHAT_MSG"


class ChatManager:
    def __init__(self, uow: AbstractUnitOfWork):
        self.uow = uow

    async def join_chat(
        self, current_user_id: uuid.UUID, user_id: uuid.UUID, chat_id: str
    ):
        async with self.uow:
            # TODO: check if chat exists
            # TODO: check if user exists
            # TODO: check if user can join this chat
            notification = ChatNotificationCreateSchema(
                chat_id=chat_id, text=USER_JOINED_CHAT_NOTIFICATION, params=str(user_id)
            )
            await self.uow.chat_repo.add_user_to_chat(chat_id=chat_id, user_id=user_id)
            _ = await self.uow.chat_repo.add_notification(notification)
            await self.uow.commit()

    async def send_message(
        self, current_user_id: uuid.UUID, message: ChatUserMessageCreateSchema
    ):
        if message.sender_id != current_user_id:
            raise UnauthorizedAction(
                detail=f"Can't send message on behalf of another user"
            )
        # TODO: check if user is allowed to send message to this chat
        async with self.uow:
            await self.uow.chat_repo.add_message(message)
            await self.uow.commit()
