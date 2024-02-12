import uuid
from services.message_broker.abstract_message_broker import AbstractMessageBroker
from services.chat_manager.chat_manager_exc import UnauthorizedAction
from services.uow.abstract_uow import AbstractUnitOfWork
from schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
)

USER_JOINED_CHAT_NOTIFICATION = "USER_JOINED_CHAT_MSG"


class ChatManager:
    def __init__(self, uow: AbstractUnitOfWork, message_broker: AbstractMessageBroker):
        self.uow = uow
        self.message_broker = message_broker

    async def subscribe_for_updates(self, current_user_id: uuid.UUID):
        async with self.uow:
            chat_list = await self.uow.chat_repo.get_joined_chat_ids(current_user_id)
            channels_list = [f"channel_{str(chat_id)}" for chat_id in chat_list]
        await self.message_broker.subscribe_list(
            channels=channels_list, user_id=current_user_id
        )

    async def join_chat(
        self, current_user_id: uuid.UUID, user_id: uuid.UUID, chat_id: str
    ):
        async with self.uow:
            # TODO: check if chat exists
            # TODO: check if user exists
            # TODO: check if user can join this chat
            notification_create = ChatNotificationCreateSchema(
                chat_id=chat_id, text=USER_JOINED_CHAT_NOTIFICATION, params=str(user_id)
            )
            await self.uow.chat_repo.add_user_to_chat(chat_id=chat_id, user_id=user_id)
            notification = await self.uow.chat_repo.add_notification(
                notification_create
            )
            await self.uow.commit()
        channel = f"chat_{str(chat_id)}"
        await self.message_broker.post_message(
            channel=channel, message=notification.model_dump_json()
        )
        await self.message_broker.subscribe(channel=channel, user_id=current_user_id)

    async def send_message(
        self, current_user_id: uuid.UUID, message: ChatUserMessageCreateSchema
    ):
        if message.sender_id != current_user_id:
            raise UnauthorizedAction(
                detail="Can't send message on behalf of another user"
            )
        # TODO: check if user is allowed to send message to this chat
        async with self.uow:
            message_in_db = await self.uow.chat_repo.add_message(message)
            await self.uow.commit()

        channel = f"channel_{str(message.chat_id)}"
        await self.message_broker.post_message(
            channel=channel, message=message_in_db.model_dump_json()
        )

    async def get_new_messages_str(
        self, current_user_id: uuid.UUID, limit: int = 20
    ) -> list[str]:
        return await self.message_broker.get_messages(
            user_id=current_user_id, limit=limit
        )
