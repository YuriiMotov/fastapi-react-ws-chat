import uuid
from abc import ABC, abstractmethod

from backend.schemas.chat import ChatCreateSchema, ChatExtSchema, ChatSchema
from backend.schemas.chat_message import (
    ChatMessageAny,
    ChatNotificationCreateSchema,
    ChatNotificationSchema,
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from backend.schemas.user import UserSchemaExt
from backend.schemas.user_chat_state import UserChatStateSchema

MAX_MESSAGE_COUNT_PER_PAGE: int = 50


class AbstractChatRepo(ABC):

    @abstractmethod
    async def add_chat(self, chat: ChatCreateSchema) -> ChatSchema:
        """
        Add chat record to the DB.

        Raises:
         - ChatRepoRequestError (duplicated chat id, ...)
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_chat(self, chat_id: uuid.UUID) -> ChatSchema | None:
        """
        Get chat by id. Returns None if chat with this ID doesn't exist.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_owned_chats(
        self, owner_id: uuid.UUID, offset: int = 0, limit: int | None = None
    ) -> list[ChatSchema]:
        """
        Get chat list by owner id.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_joined_chat_ids(
        self, user_id: uuid.UUID, offset: int = 0, limit: int | None = None
    ) -> list[uuid.UUID]:
        """
        Get list of joined chat ids by user id.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_joined_chat_list(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int | None = None,
        chat_id_list: list[uuid.UUID] | None = None,
    ) -> list[ChatExtSchema]:
        """
        Get list of joined chats by user.
        If chat_id_list is not empty list, then filter chats by this list.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def add_user_to_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """
        Add user-chat link record to the DB.

        Raises:
         - ChatRepoRequestError (user-chat link already exists)
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def add_message(
        self, message: ChatUserMessageCreateSchema
    ) -> ChatUserMessageSchema:
        """
        Add message record to the DB.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def edit_message(self, message_id: int, text: str) -> ChatUserMessageSchema:
        """
        Edit text of the message with id=message_id.

        Raises:
         - ChatRepoDatabaseError if the database fails
         - ChatRepoRequestError if there is no message with such id
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_message(self, message_id: int) -> ChatUserMessageSchema:
        """
        Get the message with id=message_id.

        Raises:
         - ChatRepoDatabaseError if the database fails
         - ChatRepoRequestError if there is no message with such id
        """
        raise NotImplementedError()

    @abstractmethod
    async def add_notification(
        self, notification: ChatNotificationCreateSchema
    ) -> ChatNotificationSchema:
        """
        Add notification record to the DB.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
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

        Returns list of pydantic objects, each of those is either ChatUserMessageSchema
        or ChatNotificationSchema objects.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_user_chat_state(
        self,
        user_id: uuid.UUID,
    ) -> list[UserChatStateSchema]:
        """
        Get data about last delivered and last read chat message for specific user.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def update_user_chat_state_from_dict(
        self, user_id: uuid.UUID, user_chat_state_dict: dict[uuid.UUID, dict[str, int]]
    ):
        """
        Updates data about last delivered and last read chat message, according to the
        data in the input dict.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_user_list(
        self,
        *,
        chat_list_filter: list[uuid.UUID] | None = None,
        name_filter: str | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[UserSchemaExt]:
        """
        Get the list of users filtered by chat_list and name filters.
        If the filter value is None, this filter doesn't have impact on results.
        Results are paginated.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_user_by_id(self, user_id: uuid.UUID) -> UserSchemaExt:
        """
        Get the User data by user's id.

        Raises:
         - ChatRepoDatabaseError if the database fails
        """
        raise NotImplementedError()
