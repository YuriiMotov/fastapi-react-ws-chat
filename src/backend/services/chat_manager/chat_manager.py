import uuid
from services.chat_manager.utils import channel_code
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
        """
        Subscribe the user to events in all their chats.
        """
        async with self.uow:
            chat_list = await self.uow.chat_repo.get_joined_chat_ids(current_user_id)
            channel_list = [channel_code("chat", chat_id) for chat_id in chat_list]
        await self.message_broker.subscribe_list(
            channels=channel_list, user_id=current_user_id
        )
        # TODO: subscribe user to other notifications (new chat, error notification, ..)

    async def join_chat(
        self, current_user_id: uuid.UUID, user_id: uuid.UUID, chat_id: uuid.UUID
    ):
        """
        Add user to chat.
        That will add User-Chat link to the DB and subscribe user to chat's events.
        In case of success, the notification will be created in DB and added to
        message broker.

        Raises:
         - UnauthorizedAction if current user unathorized to add users to that chat
         - BadRequest if user_id or chat_id is wrong
        """
        async with self.uow:
            # TODO: check if chat exists
            # TODO: check if user exists
            # TODO: check if user can join this chat (current_user is chat's owner?)

            await self.uow.chat_repo.add_user_to_chat(chat_id=chat_id, user_id=user_id)
            notification_create = ChatNotificationCreateSchema(
                chat_id=chat_id, text=USER_JOINED_CHAT_NOTIFICATION, params=str(user_id)
            )
            notification = await self.uow.chat_repo.add_notification(
                notification_create
            )
            await self.uow.commit()
        channel = channel_code("chat", chat_id)
        await self.message_broker.post_message(
            channel=channel, message=notification.model_dump_json()
        )
        await self.message_broker.subscribe(channel=channel, user_id=user_id)

    async def send_message(
        self, current_user_id: uuid.UUID, message: ChatUserMessageCreateSchema
    ):
        """
        Send message to chat.
        That will add message to the DB and to the message broker.

        Raises:
         - UnauthorizedAction if current user unathorized to send msg to that chat or if
           user_id is not equal to current_user_id (attempt to send message on behalf of
           another user)
         - BadRequest if user_id or chat_id is wrong
        """
        if message.sender_id != current_user_id:
            raise UnauthorizedAction(
                detail="Can't send message on behalf of another user"
            )
        # TODO: check if chat exists
        # TODO: check if user exists
        # TODO: check if user is allowed to send message to this chat
        async with self.uow:
            message_in_db = await self.uow.chat_repo.add_message(message)
            await self.uow.commit()

        channel = channel_code("chat", message.chat_id)
        await self.message_broker.post_message(
            channel=channel, message=message_in_db.model_dump_json()
        )

    async def get_new_messages_str(
        self, current_user_id: uuid.UUID, limit: int = 20
    ) -> list[str]:
        """
        Get messages from user's message broker queue.

        Raises:
         - UserNotSubscribedMBE(MessageBrokerException) if user is not subscribed.
        """
        return await self.message_broker.get_messages(
            user_id=current_user_id, limit=limit
        )
