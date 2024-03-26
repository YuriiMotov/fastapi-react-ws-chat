import uuid
from contextlib import contextmanager

from backend.schemas.chat import ChatExtSchema
from backend.schemas.chat_message import (
    ChatMessageAny,
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
)
from backend.schemas.event import (
    AnyEvent,
    ChatListUpdate,
    ChatMessageEvent,
    UserAddedToChatNotification,
)
from backend.services.chat_manager.chat_manager_exc import (
    BadRequest,
    EventBrokerError,
    NotSubscribedError,
    RepositoryError,
    UnauthorizedAction,
)
from backend.services.chat_manager.utils import channel_code
from backend.services.chat_repo.abstract_chat_repo import MAX_MESSAGE_COUNT_PER_PAGE
from backend.services.chat_repo.chat_repo_exc import ChatRepoException
from backend.services.event_broker.abstract_event_broker import AbstractEventBroker
from backend.services.event_broker.event_broker_exc import (
    EventBrokerException,
    EventBrokerUserNotSubscribedError,
)
from backend.services.uow.abstract_uow import AbstractUnitOfWork

USER_JOINED_CHAT_NOTIFICATION = "USER_JOINED_CHAT_MSG"


@contextmanager
def process_exceptions(*args, **kwds):
    """
    Intercept ChatRepo's and EventBroker's exceptions and raise ChatManagerException
    """
    try:
        yield
    except (ChatRepoException,) as exc:
        raise RepositoryError(detail=str(exc))
    except EventBrokerException as exc:
        raise EventBrokerError(detail=str(exc))


class ChatManager:
    def __init__(self, uow: AbstractUnitOfWork, event_broker: AbstractEventBroker):
        self.uow = uow
        self.event_broker = event_broker

    async def subscribe_for_updates(self, current_user_id: uuid.UUID):
        """
        Subscribe user to events in all their chats.

        Raises:
         - RepositoryError on repository failure
         - EventBrokerError on event broker failure
        """
        with process_exceptions():
            async with self.uow:
                chat_list = await self.uow.chat_repo.get_joined_chat_ids(
                    current_user_id
                )
                channel_list = [channel_code("chat", chat_id) for chat_id in chat_list]
            channel_list.append(channel_code("user", current_user_id))
            await self.event_broker.subscribe_list(
                channels=channel_list, user_id=current_user_id
            )

    # async def unsubscribe_from_updates(self, current_user_id: uuid.UUID):
    #     """
    #     Unsubscribe user from all events.

    #     Raises:
    #      - EventBrokerError on Event broker failure
    #     """
    #     with process_exceptions():
    #         await self.event_broker.unsubscribe(user_id=current_user_id)

    async def get_joined_chat_list(
        self, current_user_id: uuid.UUID
    ) -> list[ChatExtSchema]:
        """
        Get the list of chats where user is a member.

        Raises:
         - RepositoryError on repository failure
        """
        with process_exceptions():
            async with self.uow:
                return await self.uow.chat_repo.get_joined_chat_list(current_user_id)

    async def add_user_to_chat(
        self, current_user_id: uuid.UUID, user_id: uuid.UUID, chat_id: uuid.UUID
    ):
        """
        Add user to chat.
        That will add User-Chat link to the DB and subscribe user to chat's events.
        In case of success, the notification will be created in DB and added to
        Event broker.

        Raises:
         - UnauthorizedAction if current user unathorized to add users to that chat
         - BadRequest if chat_id is wrong
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
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
            # Post notification to the chat's channel and to the user's channel via
            # Event broker
            # TODO: catch exceptions during post_event() and retry or log
            await self.event_broker.post_event(
                channel=channel_code("chat", chat_id),
                event=ChatMessageEvent(message=notification),
            )
            await self.event_broker.post_event(
                channel=channel_code("user", user_id),
                event=UserAddedToChatNotification(chat_id=chat_id),
            )

    async def send_message(
        self, current_user_id: uuid.UUID, message: ChatUserMessageCreateSchema
    ):
        """
        Send message to chat.
        That will add message to the DB and event to the Event broker.

        Raises:
         - UnauthorizedAction if current user is not a member of that chat or if
           user_id is not equal to current_user_id (attempt to send message on behalf of
           another user)
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
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
            # Add event to the DB and to Event broker's queue
            async with self.uow:
                message_in_db = await self.uow.chat_repo.add_message(message)
                await self.uow.commit()
            channel = channel_code("chat", message.chat_id)
            await self.event_broker.post_event(
                channel=channel,
                event=ChatMessageEvent(message=message_in_db),
            )

    async def get_events(
        self, current_user_id: uuid.UUID, limit: int = 20
    ) -> list[AnyEvent]:
        """
        Get events from user's Event broker queue.

        Raises:
         - UserNotSubscribedMBE(EventBrokerException) if user is not subscribed.
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
        """
        with process_exceptions():
            try:
                events = await self.event_broker.get_events(
                    user_id=current_user_id, limit=limit
                )
                if events:
                    await self._process_events_before_send(events, current_user_id)
                return events
            except EventBrokerUserNotSubscribedError as exc:
                raise NotSubscribedError(detail=str(exc))

    async def get_message_list(
        self,
        chat_id: uuid.UUID,
        start_id: int = -1,
        order_desc: bool = True,
        limit: int = MAX_MESSAGE_COUNT_PER_PAGE,
    ) -> list[ChatMessageAny]:
        """
        Get list of chat's messages by filter (start_id).
        Note: message with id=start_id is not included int the results.

        Raises:
         - RepositoryError on repository failure
        """

        with process_exceptions():
            async with self.uow:
                return await self.uow.chat_repo.get_message_list(
                    chat_id=chat_id,
                    start_id=start_id,
                    order_desc=order_desc,
                    limit=limit,
                )

    async def acknowledge_events(self, current_user_id: uuid.UUID):
        await self.event_broker.acknowledge_events(user_id=current_user_id)

    async def _process_events_before_send(
        self, events: list[AnyEvent], current_user_id: uuid.UUID
    ):
        """
        Process events and do some actions triggered by these events.

        Raises:
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
        """
        with process_exceptions():
            for event in events:
                if isinstance(event, UserAddedToChatNotification):
                    # Subscribe user for this chat's updates
                    await self.event_broker.subscribe(
                        channel=channel_code("chat", event.chat_id),
                        user_id=current_user_id,
                    )
                    # Send chat list update data
                    async with self.uow:
                        chats = await self.uow.chat_repo.get_joined_chat_list(
                            user_id=current_user_id, chat_id_list=[event.chat_id]
                        )
                    if len(chats) != 1:
                        raise RepositoryError(
                            detail=(
                                f"get_joined_chat_list({current_user_id}, "
                                f"{[event.chat_id]}) returned {chats}"
                            )
                        )
                    await self.event_broker.post_event(
                        channel=channel_code("user", current_user_id),
                        event=ChatListUpdate(action_type="add", chat_data=chats[0]),
                    )
