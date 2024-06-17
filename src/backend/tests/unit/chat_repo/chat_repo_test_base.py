import random
import uuid

import pytest

from backend.models.user import User
from backend.schemas.chat import ChatSchema
from backend.schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
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
    # Tests for edit_message() method

    async def test_edit_message__success(self):
        """
        add_message() edits message record in the DB and returns edited message.
        """
        # Prepare data
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        message = ChatUserMessageCreateSchema(
            chat_id=chat_id, text="my message", sender_id=user_id
        )
        message_in_db = await self.repo.add_message(message)

        # Check that method returned edited message's data
        new_text = "my edited message text"
        message_edited = await self.repo.edit_message(
            message_id=message_in_db.id, text=new_text
        )

        assert message_edited.id == message_in_db.id
        assert message_edited.sender_id == user_id
        assert message_edited.text == new_text

    async def test_edit_message__bad_request_on_wrong_message_id(self):
        """
        add_message() raises ChatRepoRequestError if there is no message with message_id
        """
        message_id = random.randint(1, 100000)

        # Check that method raises exception
        new_text = "my edited message text"
        with pytest.raises(ChatRepoRequestError, match="doesnt exist"):
            await self.repo.edit_message(message_id=message_id, text=new_text)

    async def test_edit_message_database_failure(self):
        """
        edit_message() raises ChatRepoDatabaseError in case of DB failure.
        """
        # Prepare data
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        message = ChatUserMessageCreateSchema(
            chat_id=chat_id, text="my message", sender_id=user_id
        )
        message_in_db = await self.repo.add_message(message)

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to edit message with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.edit_message(message_id=message_in_db.id, text="new text")

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
        get_joined_chat_ids() method returns the list of chats joined by user with
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
    # Tests for get_joined_chat_list() method

    async def test_get_joined_chat_list(self):
        """
        get_joined_chat_list() method returns the list of chats (extended info)
        joined by user with specific user_id
        """
        chat_id = uuid.uuid4()
        user_1_id = uuid.uuid4()
        user_2_id = uuid.uuid4()
        # Create chat, add users to the chat, add message to the chat
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my_chat", owner_id=user_1_id)
        )
        await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_1_id)
        await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_2_id)
        await self.repo.add_message(
            ChatUserMessageCreateSchema(
                chat_id=chat_id, text="my message", sender_id=user_2_id
            )
        )

        # Request and check the list of chats of user_1
        chats = await self.repo.get_joined_chat_list(user_id=user_1_id)
        assert chats is not None
        assert len(chats) == 1
        assert chats[0].members_count == 2
        assert chats[0].last_message_text == "my message"

    async def test_get_joined_chat_list_no_messages(self):
        """
        get_joined_chat_list() method returns the list of chats (extended info)
        joined by user with specific user_id.
        Field last_message_text is None when there are no messages in the chat
        """
        chat_id = uuid.uuid4()
        user_1_id = uuid.uuid4()
        user_2_id = uuid.uuid4()
        # Create chat, add users to the chat
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my_chat", owner_id=user_1_id)
        )
        await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_1_id)
        await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_2_id)

        # Request and check the list of chats of user_1
        chats = await self.repo.get_joined_chat_list(user_id=user_1_id)
        assert chats is not None
        assert len(chats) == 1
        assert chats[0].last_message_text is None

    async def test_get_joined_chat_list_filtered_by_id_list(self):
        """
        get_joined_chat_list() method returns the list of chats (extended info)
        joined by user with specific user_id, filtered by the list od IDs if it's
        passed as a parameter.
        """
        chat_id_list = [uuid.uuid4() for _ in range(5)]
        user_1_id = uuid.uuid4()
        # Create chats, add user to the chat
        for chat_id in chat_id_list:
            await self.repo.add_chat(
                ChatSchema(id=chat_id, title=f"my_chat {chat_id}", owner_id=user_1_id)
            )
            await self.repo.add_user_to_chat(chat_id=chat_id, user_id=user_1_id)

        filter_id_list = chat_id_list[::2]  # With indexes 0, 2, 4

        # Request and check the list of chats of user_1
        chats = await self.repo.get_joined_chat_list(
            user_id=user_1_id, chat_id_list=filter_id_list
        )
        assert chats is not None
        assert len(chats) == len(filter_id_list)
        assert {chat.id for chat in chats} == set(filter_id_list)

    async def test_get_joined_chat_list_database_failure(self):
        """
        get_joined_chat_list() raises ChatRepoDatabaseError in case of
        DB failure.
        """
        user_1_id = uuid.uuid4()

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to add message with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.get_joined_chat_list(user_1_id)

    # ---------------------------------------------------------------------------------
    # Tests for get_message_list() method

    async def test_get_message_list_successful(self):
        """
        get_message_list() method returns list of chat's messages.
        Message list contains user messages and notifications.
        There are also messages in the another chat.
        """
        first_chat_id = uuid.uuid4()
        another_chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        messages = {
            first_chat_id: [f"message {uuid.uuid4()}" for _ in range(3)],
            another_chat_id: [f"message {uuid.uuid4()}" for _ in range(3)],
        }
        notifications = {
            first_chat_id: [f"notification {uuid.uuid4()}" for _ in range(3)],
            another_chat_id: [f"notification {uuid.uuid4()}" for _ in range(3)],
        }
        first_chat_all_messages = set(messages[first_chat_id]) | set(
            notifications[first_chat_id]
        )
        # Create chats, add messages and notifications to these chats
        await self.repo.add_chat(
            ChatSchema(id=first_chat_id, title="my_chat", owner_id=user_id)
        )
        for chat_id, chat_messages in messages.items():
            for chat_message in chat_messages:
                await self.repo.add_message(
                    ChatUserMessageCreateSchema(
                        chat_id=chat_id, text=chat_message, sender_id=user_id
                    )
                )
        for chat_id, chat_notification in notifications.items():
            for chat_message in chat_notification:
                await self.repo.add_notification(
                    ChatNotificationCreateSchema(
                        chat_id=chat_id, text=chat_message, params=str(uuid.uuid4())
                    )
                )

        # Request messages from first_chat, check them
        messages_res = await self.repo.get_message_list(chat_id=first_chat_id)
        assert len(messages_res) == len(first_chat_all_messages)
        assert {msg.text for msg in messages_res} == set(first_chat_all_messages)

    @pytest.mark.parametrize("order_desc", (True, False))
    @pytest.mark.parametrize("start_index", (None, 1, 2))
    @pytest.mark.parametrize("limit", (100, 1))
    async def test_get_message_list_order_and_filter(
        self, order_desc: bool, start_index: int | None, limit: int
    ):
        """
        get_message_list() method returns list of messages filtered by start_id,
        ordered and limited.
        """
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        messages = [f"message {uuid.uuid4()}" for _ in range(3)]
        # Create chat, add messages thшы chat
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my_chat", owner_id=user_id)
        )
        messages_db: list[ChatUserMessageSchema] = []
        for chat_message in messages:
            msg = await self.repo.add_message(
                ChatUserMessageCreateSchema(
                    chat_id=chat_id, text=chat_message, sender_id=user_id
                )
            )
            messages_db.append(msg)
        start_id = messages_db[start_index].id if (start_index is not None) else -1
        expected_ids = filter_and_sort_messages(
            messages_db, order_desc=order_desc, start_id=start_id, limit=limit
        )

        # Request messages from first_chat, check them
        messages_res = await self.repo.get_message_list(
            chat_id=chat_id, start_id=start_id, order_desc=order_desc, limit=limit
        )
        message_ids_res = [msg.id for msg in messages_res]
        assert len(expected_ids) == len(message_ids_res)
        assert message_ids_res == expected_ids

    async def test_user_chat_state_update__all_new(self):
        """
        update_user_chat_state_from_dict() updates chat status data for specific user
        according to the input dict.

        No any records exist in the DB for this user.
        Input dict contains items with different set of fields.
        """
        user_id = uuid.uuid4()
        user_chat_state_dict = {
            uuid.uuid4(): {"last_delivered": random.randint(1, 100)},
            uuid.uuid4(): {"last_read": random.randint(1, 100)},
            uuid.uuid4(): {
                "last_delivered": random.randint(1, 100),
                "last_read": random.randint(1, 100),
            },
        }
        expected_data_set = {
            (chat_id, state.get("last_delivered", 0), state.get("last_read", 0))
            for chat_id, state in user_chat_state_dict.items()
        }
        await self.repo.update_user_chat_state_from_dict(user_id, user_chat_state_dict)

        user_chat_state_data = await self.repo.get_user_chat_state(user_id)
        real_data_set = {
            (state.chat_id, state.last_delivered, state.last_read)
            for state in user_chat_state_data
        }

        assert len(real_data_set) == len(expected_data_set)
        assert real_data_set == expected_data_set, real_data_set

    async def test_user_chat_state_update__all_existed(self):
        """
        update_user_chat_state_from_dict() updates chat status data for specific user
        according to the input dict.

        All the records already exist in the DB for this user.
        """
        user_id = uuid.uuid4()
        await self.repo.update_user_chat_state_from_dict(
            user_id,
            {
                uuid.uuid4(): {"last_delivered": 4, "last_read": 1},
                uuid.uuid4(): {"last_delivered": 5, "last_read": 2},
                uuid.uuid4(): {"last_delivered": 6, "last_read": 3},
            },
        )
        user_chat_state_data_prev = await self.repo.get_user_chat_state(user_id)
        user_chat_state_dict = {
            state.chat_id: {
                "last_delivered": state.last_delivered + 1,
                "last_read": state.last_read + 1,
            }
            for state in user_chat_state_data_prev
        }
        expected_data_set = {
            (chat_id, state["last_delivered"], state["last_read"])
            for chat_id, state in user_chat_state_dict.items()
        }
        await self.repo.update_user_chat_state_from_dict(user_id, user_chat_state_dict)

        user_chat_state_data = await self.repo.get_user_chat_state(user_id)
        real_data_set = {
            (state.chat_id, state.last_delivered, state.last_read)
            for state in user_chat_state_data
        }
        assert len(real_data_set) == len(expected_data_set)
        assert real_data_set == expected_data_set

    # ---------------------------------------------------------------------------------
    # Tests for get_message_list() method

    async def test_get_user_list__success(self):
        """
        get_user_list() returns list of chat members.
        """
        data = await self.create_users_and_chats()
        await self.repo.add_user_to_chat(data["chat_1"].id, data["user_1"].id)
        await self.repo.add_user_to_chat(data["chat_2"].id, data["user_1"].id)
        await self.repo.add_user_to_chat(data["chat_1"].id, data["user_2"].id)
        await self.repo.add_user_to_chat(data["chat_2"].id, data["user_2"].id)
        await self.repo.add_user_to_chat(data["chat_3"].id, data["user_2"].id)
        await self.repo.add_user_to_chat(data["chat_3"].id, data["user_3"].id)
        # U1 and U2 have 2 mutual chats (1, 2), U2 and U3 have 1 mutual chat (3),
        # U1 and U3 have no mutual chats

        users = await self.repo.get_user_list([data["chat_1"].id, data["chat_2"].id])
        assert len(users) == 2
        user_ids = [user.id for user in users]
        assert data["user_1"].id in user_ids
        assert data["user_2"].id in user_ids

    async def test_get_user_list__empty_list(self):
        """
        get_user_list() returns empty list if the input chat list is empty or
        there are no users in chats.
        """
        data = await self.create_users_and_chats()

        users = await self.repo.get_user_list([])
        assert len(users) == 0
        users = await self.repo.get_user_list([data["chat_1"].id])
        assert len(users) == 0

    async def test_get_user_list__database_failure(self):
        """
        get_user_list() raises ChatRepoDatabaseError in case of
        DB failure.
        """
        data = await self.create_users_and_chats()

        # Mock DB connection to make it always return error
        await self._break_connection()

        # Attempt to call `get_user_list` with no DB connection
        with pytest.raises(ChatRepoDatabaseError):
            await self.repo.get_user_list([data["chat_1"].id])

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

    # ---------------------------------------------------------------------------------
    # Helper methods

    async def create_users_and_chats(self) -> dict[str, User | ChatSchema]:
        """
        Create 3 users and 3 chats
        """
        user_1 = await self._create_user(uuid.uuid4())
        user_2 = await self._create_user(uuid.uuid4())
        user_3 = await self._create_user(uuid.uuid4())
        chat_1_id = uuid.uuid4()
        chat_1 = await self.repo.add_chat(
            ChatSchema(id=chat_1_id, title=f"chat_{chat_1_id}", owner_id=user_3.id)
        )
        chat_2_id = uuid.uuid4()
        chat_2 = await self.repo.add_chat(
            ChatSchema(id=chat_2_id, title=f"chat_{chat_2_id}", owner_id=user_3.id)
        )
        chat_3_id = uuid.uuid4()
        chat_3 = await self.repo.add_chat(
            ChatSchema(id=chat_3_id, title=f"chat_{chat_3_id}", owner_id=user_3.id)
        )
        return dict(
            user_1=user_1,
            user_2=user_2,
            user_3=user_3,
            chat_1=chat_1,
            chat_2=chat_2,
            chat_3=chat_3,
        )


# ---------------------------------------------------------------------------------
# Helper functions


def filter_and_sort_messages(
    messages: list[ChatUserMessageSchema],
    order_desc: bool,
    start_id: int,
    limit: int,
):
    if start_id >= 0:
        messages_res = list(
            filter(
                lambda x: ((x.id < start_id) if order_desc else (x.id > start_id)),
                messages,
            )
        )
    else:
        messages_res = list(messages)
    messages_res.sort(key=lambda x: x.id, reverse=order_desc)
    messages_res = messages_res[:limit]
    return [msg.id for msg in messages_res]
