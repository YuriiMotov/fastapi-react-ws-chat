import uuid

import pytest

from backend.models.user import User
from backend.schemas.chat import ChatSchema
from backend.schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
)
from backend.services.chat_repo.abstract_chat_repo import AbstractChatRepo
from backend.services.chat_repo.chat_repo_exc import (
    ChatRepoDatabaseError,
    ChatRepoRequestError,
)


class ChatRepoTestBase:
    """
    Base class for testing concrete implementations of AbstractChatRepo interface.

    To add tests for a concrete class:
     - create a descendant class from ChatRepoTestBase
     - add fixture (with autouse=True) that initializes self.repo with the concrete
        implementation of the AbstractChatRepo interface
     - implement abstract methods (_check_if_chat_has_persisted,
        _check_if_message_has_persisted, etc..)
    """

    repo: AbstractChatRepo  # Should be initialized by fixture

    # ---------------------------------------------------------------------------------
    # Tests for add_chat() method

    async def test_add_chat(self):
        """
        add_chat() creates Chat record in the DB and returns created record's data.
        """
        # Prepare data
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chat_before = ChatSchema(id=chat_id, title="my chat", owner_id=user_id)

        # Call repo.add_chat()
        chat_after = await self.repo.add_chat(chat_before)

        # Check that method returned created record's data
        assert chat_after.id == chat_before.id
        assert chat_after.title == chat_before.title
        assert chat_after.owner_id == chat_before.owner_id

        # Check that the record was persisted in the DB
        assert (await self._check_if_chat_has_persisted(chat_id)) is True

    async def test_add_chat_duplicated_id(self):
        """
        add_chat() raises ChatRepoRequestError if the record with chat_id already
        exists.
        """
        # Prepare data, create chat
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        another_user_id = uuid.uuid4()
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        )

        # Attempt to create chat with the same chat_id lead to the error
        with pytest.raises(ChatRepoRequestError):
            await self.repo.add_chat(
                ChatSchema(id=chat_id, title="another chat", owner_id=another_user_id)
            )

    async def test_add_chat_database_failure(self):
        """
        add_chat() raises ChatRepoDatabaseError in case of DB failure.
        """
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to create chat with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.add_chat(
                ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
            )

    # ---------------------------------------------------------------------------------
    # Tests for get_chat() method

    async def test_get_chat(self):
        """
        get_chat() returns Chat record.
        """
        # Prepare data, create chat
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chat_before = ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        await self.repo.add_chat(chat_before)
        assert (await self._check_if_chat_has_persisted(chat_id)) is True

        # Request chat from repo by ID
        chat_from_db = await self.repo.get_chat(chat_id)
        assert chat_from_db is not None
        assert chat_from_db.id == chat_before.id
        assert chat_from_db.title == chat_before.title
        assert chat_from_db.owner_id == chat_before.owner_id

    async def test_get_chat_not_exist(self):
        """
        get_chat() returns None if chat with this ID doesn't exist.
        """
        chat_id = uuid.uuid4()

        # Request chat from repo by ID
        chat_from_db = await self.repo.get_chat(chat_id)
        assert chat_from_db is None

    async def test_get_chat_database_failure(self):
        """
        get_chat() raises ChatRepoDatabaseError in case of DB failure.
        """
        chat_id = uuid.uuid4()

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to create chat with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.get_chat(chat_id=chat_id)

    # ---------------------------------------------------------------------------------
    # Tests for add_message() method

    async def test_add_message(self):
        """
        add_message() creates ChatUserMessage record in the DB and returns created
        record's data.
        """
        # Prepare data
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        message_before = ChatUserMessageCreateSchema(
            chat_id=chat_id, text="my message", sender_id=user_id
        )

        # Call repo.add_message()
        message_after = await self.repo.add_message(message_before)

        # Check that method returned created record's data
        assert message_after.id > 0
        assert message_after.dt is not None
        assert message_after.chat_id == message_before.chat_id
        assert message_after.text == message_before.text
        assert message_after.sender_id == message_before.sender_id

        # Check that the record was persisted in the DB
        assert (await self._check_if_message_has_persisted(message_after.id)) is True

    async def test_add_message_database_failure(self):
        """
        add_message() raises ChatRepoDatabaseError in case of DB failure.
        """
        # Prepare data
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        message = ChatUserMessageCreateSchema(
            chat_id=chat_id, text="my message", sender_id=user_id
        )

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to add message with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.add_message(message)

    # ---------------------------------------------------------------------------------
    # Tests for add_notification() method

    async def test_add_notification(self):
        """
        add_notification() creates ChatNotification record in the DB and returns created
        record's data.
        """
        # Prepare data, create chat
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        )
        notification_before = ChatNotificationCreateSchema(
            chat_id=chat_id, text="notification", params=str(uuid.uuid4())
        )

        # Call repo.add_notification()
        notification_after = await self.repo.add_notification(notification_before)

        # Check that method returned created record's data
        assert notification_after.id > 0
        assert notification_after.dt is not None
        assert notification_after.chat_id == notification_before.chat_id
        assert notification_after.text == notification_before.text
        assert notification_after.params == notification_before.params

        # Check that the record was persisted in the DB
        assert (
            await self._check_if_message_has_persisted(notification_after.id)
        ) is True

    async def test_add_notification_database_failure(self):
        """
        add_notification() raises ChatRepoDatabaseError in case of DB failure.
        """
        # Prepare data
        chat_id = uuid.uuid4()
        notification = ChatNotificationCreateSchema(
            chat_id=chat_id, text="notification", params=str(uuid.uuid4())
        )

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to add message with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.add_notification(notification)

    # ---------------------------------------------------------------------------------
    # Tests for get_owned_chats() method

    async def test_get_owned_chats(self):
        """
        get_owned_chats() method returns the list of chats owned by user with specific
        user_id
        """
        user_1_id = uuid.uuid4()
        user_2_id = uuid.uuid4()
        user_1_chat_ids = [uuid.uuid4() for _ in range(3)]
        user_2_chat_ids = [uuid.uuid4() for _ in range(3)]
        # Create chats for user_1 and user_2
        for chat_id in user_1_chat_ids:
            await self.repo.add_chat(
                ChatSchema(id=chat_id, title="my chat", owner_id=user_1_id)
            )
        for chat_id in user_2_chat_ids:
            await self.repo.add_chat(
                ChatSchema(id=chat_id, title="my chat", owner_id=user_2_id)
            )

        # Request and check the list of chats, where user_1 is owner
        user_1_chats_res = await self.repo.get_owned_chats(owner_id=user_1_id)
        assert len(user_1_chats_res) == len(user_1_chat_ids)
        for i in range(len(user_1_chats_res)):
            assert user_1_chats_res[i].id == user_1_chat_ids[i]

        # Request and check the list of chats, where user_2 is owner
        user_2_chats_res = await self.repo.get_owned_chats(owner_id=user_2_id)
        assert len(user_2_chats_res) == len(user_2_chat_ids)
        for i in range(len(user_2_chats_res)):
            assert user_2_chats_res[i].id == user_2_chat_ids[i]

    async def test_get_owned_chats_database_failure(self):
        """
        get_owned_chats() raises ChatRepoDatabaseError in case of DB failure.
        """
        user_1_id = uuid.uuid4()

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to add message with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.get_owned_chats(user_1_id)

    # ---------------------------------------------------------------------------------
    # Tests for add_user_to_chat() method

    async def test_add_user_to_chat(self):
        """
        add_user_to_chat() method creates UserChatLink record in the DB.
        """
        # Create user and chats
        chat_owner_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await self._create_user(user_id=user_id)
        chat_list = [uuid.uuid4() for _ in range(3)]
        for chat_id in chat_list:
            await self.repo.add_chat(
                ChatSchema(id=chat_id, title="chat", owner_id=chat_owner_id)
            )

        # Add user to chats
        for chat_id in chat_list:
            await self.repo.add_user_to_chat(user_id=user_id, chat_id=chat_id)

        # Request and check the list of chats joined by user
        chat_list_res = await self.repo.get_joined_chat_ids(user_id=user_id)
        assert chat_list_res is not None
        assert len(chat_list_res) == len(chat_list)
        assert set(chat_list_res) == set(chat_list)

    async def test_add_user_to_chat_already_added(self):
        """
        add_user_to_chat() method raises ChatRepoRequestError error if user has already
        joined this chat.
        """
        # Create user, add user to chat
        user_id = uuid.uuid4()
        await self._create_user(user_id=user_id)
        chat_id = uuid.uuid4()
        await self.repo.add_user_to_chat(user_id=user_id, chat_id=chat_id)

        # Try adding user to chat again, check that it raises ChatRepoRequestError
        with pytest.raises(ChatRepoRequestError):
            await self.repo.add_user_to_chat(user_id=user_id, chat_id=chat_id)

    async def test_add_user_to_chat_database_failure(self):
        """
        add_user_to_chat() raises ChatRepoDatabaseError in case of DB failure.
        """
        # Create user, add user to chat
        user_id = uuid.uuid4()
        await self._create_user(user_id=user_id)
        chat_id = uuid.uuid4()

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Try adding user to chat again, check that it raises ChatRepoRequestError
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.add_user_to_chat(user_id=user_id, chat_id=chat_id)

    # ---------------------------------------------------------------------------------
    # Tests for get_joined_chat_ids() method

    async def test_get_joined_chat_ids(self):
        """
        get_joined_chat_ids() method returns the list of chats owned by user with
        specific user_id
        """
        user_1_id = uuid.uuid4()
        user_2_id = uuid.uuid4()
        user_1_chat_ids = [uuid.uuid4() for _ in range(3)]
        user_2_chat_ids = [uuid.uuid4() for _ in range(3)]
        # Add user_1 to their chats
        for chat_id in user_1_chat_ids:
            await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_1_id)
        # Add user_2 to their chats
        for chat_id in user_2_chat_ids:
            await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_2_id)

        # Request and check the list of chats of user_1
        user_1_chats_res = await self.repo.get_joined_chat_ids(user_id=user_1_id)
        assert user_1_chats_res is not None
        assert len(user_1_chats_res) == len(user_1_chat_ids)
        assert set(user_1_chats_res) == set(user_1_chat_ids)

        # Request and check the list of chats of user_2
        user_2_chats_res = await self.repo.get_joined_chat_ids(user_id=user_2_id)
        assert user_2_chats_res is not None
        assert len(user_2_chats_res) == len(user_2_chat_ids)
        assert set(user_2_chats_res) == set(user_2_chat_ids)

    async def test_get_joined_chat_ids_database_failure(self):
        """
        get_joined_chat_ids() raises ChatRepoDatabaseError in case of DB failure.
        """
        user_1_id = uuid.uuid4()

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to add message with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.get_joined_chat_ids(user_1_id)

    # ---------------------------------------------------------------------------------
    # Tests for get_joined_chat_ext_info() method

    async def test_get_joined_chat_ext_info(self):
        """
        get_joined_chat_ids() method returns the list of chats owned by user with
        specific user_id
        """
        chat_id = uuid.uuid4()
        user_1_id = uuid.uuid4()
        user_2_id = uuid.uuid4()
        # Create chat and add users to the chat
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my_chat", owner_id=user_1_id)
        )
        await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_1_id)
        # Add user_2 to their chats
        await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_2_id)

        # Request and check the list of chats of user_1
        chats = await self.repo.get_joined_chat_ext_info(user_id=user_1_id)
        assert chats is not None
        assert len(chats) == 1
        assert chats[0].members_count == 2

    # ---------------------------------------------------------------------------------
    # Methods below should be implemented in the descendant class

    async def _check_if_chat_has_persisted(self, chat_id: uuid.UUID) -> bool:
        raise NotImplementedError()

    async def _check_if_message_has_persisted(self, message_id: int) -> bool:
        raise NotImplementedError()

    async def _check_if_user_chat_link_has_persisted(
        self, user_id: uuid.UUID, chat_id: uuid.UUID
    ) -> bool:
        raise NotImplementedError()

    async def _create_user(self, user_id: uuid.UUID) -> User:
        raise NotImplementedError()

    async def _break_connection(self):
        raise NotImplementedError()
