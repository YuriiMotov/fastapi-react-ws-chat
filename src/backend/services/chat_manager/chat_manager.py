import uuid
from contextlib import contextmanager

from backend.schemas.chat_message import (
    ChatMessageAny,
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
)
from backend.services.chat_manager.chat_manager_exc import (
    BadRequest,
    MessageBrokerError,
    NotSubscribedError,
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.chat_repo.abstract_chat_repo import MAX_MESSAGE_COUNT_PER_PAGE
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.message_broker.abstract_message_broker import (
    AbstractMessageBroker,
)
from backend.services.message_broker.message_broker_exc import (
    MessageBrokerException,
    MessageBrokerUserNotSubscribedError,
)
from backend.services.uow.abstract_uow import AbstractUnitOfWork

USER_JOINED_CHAT_NOTIFICATION = "USER_JOINED_CHAT_MSG"


@contextmanager
def process_exceptions(*args, **kwds):
    """
    Intercept ChatRepo's and MessageBroker's exceptions and raise ChatManagerException
    """
    try:
        yield
    except (ChatRepoException,) as exc:
        raise RepositoryError(detail=str(exc))
    except MessageBrokerException as exc:
        raise MessageBrokerError(detail=str(exc))


class ChatManager:
    def __init__(self, uow: AbstractUnitOfWork, message_broker: AbstractMessageBroker):
        self.uow = uow
        self.message_broker = message_broker

    async def subscribe_for_updates(self, current_user_id: uuid.UUID):
        """
        Subscribe user to events in all their chats.

        Raises:
         - RepositoryError on repository failure
         - MessageBrokerError on message broker failure
        """
        with process_exceptions():
            async with self.uow:
                chat_list = await self.uow.chat_repo.get_joined_chat_ids(
                    current_user_id
                )
                channel_list = [channel_code("chat", chat_id) for chat_id in chat_list]
            await self.message_broker.subscribe_list(
                channels=channel_list, user_id=current_user_id
            )
            # TODO: subscribe user to other notifications
            # (new chat, error notification, ..)

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
         - BadRequest if chat_id is wrong
         - RepositoryError on repository failure
         - MessageBrokerError on message broker failure
        """
        with process_exceptions():
            async with self.uow:
                # Check request (chat exists, current_user is authorized to add users
                # to the chat)
                chat = await self.uow.chat_repo.get_chat(chat_id=chat_id)
                if chat is None:
                    raise BadRequest(detail=f"Chat with ID={chat_id} doesn't exist")
                if chat.owner_id != current_user_id:
                    raise UnauthorizedAction(
                        detail=f"User ({current_user_id} unauthorized to add users to"
                        f"chat ({chat_id}))"
                    )
                # Make changes in DB and add notification to DB
                await self.uow.chat_repo.add_user_to_chat(
                    chat_id=chat_id, user_id=user_id
                )
                notification_create = ChatNotificationCreateSchema(
                    chat_id=chat_id,
                    text=USER_JOINED_CHAT_NOTIFICATION,
                    params=str(user_id),
                )
                notification = await self.uow.chat_repo.add_notification(
                    notification_create
                )
                await self.uow.commit()
            # Post notification to the message broker's queue, subscribe to notif-s
            channel = channel_code("chat", chat_id)
            # TODO: catch exceptions during post_message() and retry or log
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
         - UnauthorizedAction if current user is not a member of that chat or if
           user_id is not equal to current_user_id (attempt to send message on behalf of
           another user)
         - RepositoryError on repository failure
         - MessageBrokerError on message broker failure
        """
        with process_exceptions():
            # Check that user is authorized to send message to this chat
            if message.sender_id != current_user_id:
                raise UnauthorizedAction(
                    detail="Can't send message on behalf of another user"
                )
            async with self.uow:
                user_chats = await self.uow.chat_repo.get_joined_chat_ids(
                    user_id=current_user_id
                )  # TODO: Add user_chats caching
            chat_id = message.chat_id
            if chat_id not in user_chats:
                raise UnauthorizedAction(
                    detail=f"User {current_user_id} is not a member of chat {chat_id}"
                )
            # Add message to the DB and to message broker's queue
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
         - RepositoryError on repository failure
         - MessageBrokerError on message broker failure
        """
        with process_exceptions():
            try:
                return await self.message_broker.get_messages(
                    user_id=current_user_id, limit=limit
                )
            except MessageBrokerUserNotSubscribedError as exc:
                raise NotSubscribedError(detail=str(exc))

    async def get_chat_message_list(
        self,
        chat_id: uuid.UUID,
        start_id: int = -1,
        order_desc: bool = True,
        limit: int = MAX_MESSAGE_COUNT_PER_PAGE,
    ) -> list[ChatMessageAny]:
        """
        TODO: add description, error handling, tests
        """

        with process_exceptions():
            async with self.uow:
                return await self.uow.chat_repo.get_message_list(
                    chat_id=chat_id,
                    start_id=start_id,
                    order_desc=order_desc,
                    limit=limit,
                )
