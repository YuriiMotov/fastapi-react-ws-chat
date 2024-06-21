import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from backend.schemas.chat import ChatExtSchema, ChatSchemaCreate
from backend.schemas.chat_message import (
    ChatMessageAny,
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from backend.schemas.event import (
    AnotherUserJoinedChatNotification,
    AnyEvent,
    ChatListUpdate,
    ChatMessageEdited,
    ChatMessageEvent,
    FirstCircleUserListUpdate,
    UserAddedToChatNotification,
)
from backend.schemas.user import UserSchema, UserSchemaExt
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
        self._user_chat_ids_cached: Optional[list[uuid.UUID]] = None
        self._first_circle_user_id_list: list[uuid.UUID] = []
        self._first_circle_user_list_updated: datetime = datetime.now() - timedelta(
            days=10 * 365
        )

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
                chat_list = await self.uow.chat_repo.get_joined_chat_list(
                    current_user_id
                )
                return chat_list

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
            # Post notifications to the chat's channel and to the user's channel via
            # Event broker
            # TODO: catch exceptions during post_event() and retry or log
            await self.event_broker.post_event(
                channel=channel_code("chat", chat_id),
                event=ChatMessageEvent(message=notification),
            )
            await self.event_broker.post_event(
                channel=channel_code("chat", chat_id),
                event=AnotherUserJoinedChatNotification(),
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
            user_chats = await self._get_joined_chat_ids(
                current_user_id=current_user_id
            )
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

    async def edit_message(
        self, current_user_id: uuid.UUID, message_id: int, text: str
    ):
        """
        Edit message with specified id and sender_id.
        Initiates a chat Event to send edited message to all chat users

        Raises:
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
         - UnauthorizedAction on attempt to edit another user's message
        """
        with process_exceptions():
            async with self.uow:
                message = await self.uow.chat_repo.get_message(message_id=message_id)
                if message.sender_id != current_user_id:
                    raise UnauthorizedAction(detail="Can't edit another user's message")
                message = await self.uow.chat_repo.edit_message(
                    message_id=message_id, text=text
                )
                await self.event_broker.post_event(
                    channel=channel_code("chat", message.chat_id),
                    event=ChatMessageEdited(message=message),
                )
                await self.uow.commit()

    async def get_events(
        self, current_user_id: uuid.UUID, limit: int = 20
    ) -> list[AnyEvent]:
        """
        Get events from user's Event broker queue.

        Raises:
         - UserNotSubscribedMBE(EventBrokerException) if user is not subscribed.
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
         - BadRequest on wrong message id or sender_id
        """
        with process_exceptions():
            try:
                events = await self.event_broker.get_events(
                    user_id=current_user_id, limit=limit
                )
                if events:
                    await self._process_events_before_send(
                        current_user_id=current_user_id, events=events
                    )
                return events
            except EventBrokerUserNotSubscribedError as exc:
                raise NotSubscribedError(detail=str(exc))

    async def get_message_list(
        self,
        current_user_id: uuid.UUID,
        chat_id: uuid.UUID,
        start_id: int = -1,
        order_desc: bool = True,
        limit: int = MAX_MESSAGE_COUNT_PER_PAGE,
    ) -> list[ChatMessageAny]:
        """
        Get list of chat's messages by filter (start_id).
        Note: message with id=start_id is not included int the results.

        Raises:
         - UnauthorizedAction if current user is not a member of that chat
         - RepositoryError on repository failure
        """

        with process_exceptions():
            user_chats = await self._get_joined_chat_ids(
                current_user_id=current_user_id
            )
            async with self.uow:
                if chat_id not in user_chats:
                    raise UnauthorizedAction(
                        detail=(
                            f"User {current_user_id} is not a member of chat {chat_id}"
                        )
                    )
                return await self.uow.chat_repo.get_message_list(
                    chat_id=chat_id,
                    start_id=start_id,
                    order_desc=order_desc,
                    limit=limit,
                )

    async def acknowledge_events(self, current_user_id: uuid.UUID):
        """
        Acknowledge receiving events that were sent to client.

        Raises:
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
        """
        with process_exceptions():
            events = await self.event_broker.acknowledge_events(user_id=current_user_id)
            await self._process_events_after_acknowledgement(
                current_user_id=current_user_id,
                events=events,
            )

    async def get_first_circle_user_list(
        self, current_user_id: uuid.UUID, full: bool = False
    ):
        """
        Sends via EventBroker the FirstCircleUserListUpdate event with the list of
        users that have mutual chats with current user.
        That list includes current user itself.

        Raises:
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
        """
        with process_exceptions():
            u_list_upd = await self._get_first_circle_user_list_updates(
                current_user_id=current_user_id, full=full
            )
            if u_list_upd:
                await self.event_broker.post_event(
                    channel=channel_code("user", current_user_id),
                    event=FirstCircleUserListUpdate(
                        is_full=False,
                        users=[UserSchema.model_validate(user) for user in u_list_upd],
                    ),
                )

    async def get_user_list(
        self,
        name_filter: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[UserSchema]:
        """
        Get list of users filtered by name with pagination.

        Raises:
         - RepositoryError on repository failure
        """
        with process_exceptions():
            async with self.uow:
                users = await self.uow.chat_repo.get_user_list(
                    name_filter=name_filter, limit=limit, offset=offset
                )
                return [UserSchema.model_validate(user) for user in users]

    async def create_chat(
        self,
        current_user_id: uuid.UUID,
        chat_data: ChatSchemaCreate,
    ):
        """
        Create chat with specified parameters. Add owner to that chat.

        Raises:
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
        """
        if chat_data.owner_id != current_user_id:
            raise UnauthorizedAction(
                detail="Can't create chat on behalf of another user"
            )
        with process_exceptions():
            async with self.uow:
                chat = await self.uow.chat_repo.add_chat(chat=chat_data)
                await self.uow.commit()
            await self.add_user_to_chat(
                current_user_id=current_user_id,
                user_id=current_user_id,
                chat_id=chat.id,
            )

    async def _get_first_circle_user_list_updates(
        self, current_user_id: uuid.UUID, full: bool = False
    ) -> list[UserSchemaExt]:
        """
        Get updates of the list of users that have mutual chats with current user.
        That list includes current user itself.

        Raises:
         - RepositoryError on repository failure
        """
        if full:
            self._first_circle_user_id_list = []
        with process_exceptions():
            chat_ids = await self._get_joined_chat_ids(current_user_id=current_user_id)
            async with self.uow:
                user_list = await self.uow.chat_repo.get_user_list(
                    chat_list_filter=chat_ids
                )
            res: list[UserSchemaExt] = []
            first_circle_user_id_list: list[uuid.UUID] = []
            for user in user_list:
                if user.id in self._first_circle_user_id_list:
                    if user.updated_at > self._first_circle_user_list_updated:
                        res.append(user)
                else:
                    res.append(user)
                self._first_circle_user_list_updated = max(
                    self._first_circle_user_list_updated, user.updated_at
                )
                first_circle_user_id_list.append(user.id)
            self._first_circle_user_id_list = first_circle_user_id_list
            return res

    async def _process_events_before_send(
        self, current_user_id: uuid.UUID, events: list[AnyEvent]
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
                if isinstance(event, UserAddedToChatNotification) or isinstance(
                    event, AnotherUserJoinedChatNotification
                ):
                    await self.get_first_circle_user_list(
                        current_user_id=current_user_id
                    )

    async def _process_events_after_acknowledgement(
        self, current_user_id: uuid.UUID, events: list[AnyEvent]
    ):
        """
        Process acknowledged events and do some actions triggered by these events.

        Raises:
         - RepositoryError on repository failure
         - EventBrokerError on Event broker failure
        """
        with process_exceptions():
            user_chat_state_dict: dict[uuid.UUID, dict[str, int]] = {}
            for event in events:
                if isinstance(event, ChatMessageEvent):
                    if isinstance(event.message, ChatUserMessageSchema):
                        prev = user_chat_state_dict.get(event.message.chat_id)
                        if prev:
                            prev["last_delivered"] = max(
                                prev["last_delivered"], event.message.id
                            )
                        else:
                            user_chat_state_dict[event.message.chat_id] = {
                                "last_delivered": event.message.id
                            }
            if user_chat_state_dict:
                async with self.uow:
                    await self.uow.chat_repo.update_user_chat_state_from_dict(
                        user_id=current_user_id,
                        user_chat_state_dict=user_chat_state_dict,
                    )
                    await self.uow.commit()

    async def _get_joined_chat_ids(self, current_user_id: uuid.UUID) -> list[uuid.UUID]:
        async with self.uow:
            if self._user_chat_ids_cached is not None:
                return self._user_chat_ids_cached
            else:
                return await self.uow.chat_repo.get_joined_chat_ids(
                    user_id=current_user_id
                )
