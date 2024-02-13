import uuid
from schemas.chat import ChatSchema
from services.chat_repo.abstract_chat_repo import AbstractChatRepo
from schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
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

        # Check that method returned created rocord's data
        assert chat_after.id == chat_before.id
        assert chat_after.title == chat_before.title
        assert chat_after.owner_id == chat_before.owner_id

        # Check that the record was persisted in the DB
        assert (await self._check_if_chat_has_persisted(chat_id)) is True

    async def test_add_message(self):
        """
        add_message() creates ChatUserMessage record in the DB and returns created
        record's data.
        """
        # Prepare data, create chat
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        )
        message_before = ChatUserMessageCreateSchema(
            chat_id=chat_id, text="my message", sender_id=user_id
        )

        # Call repo.add_message()
        message_after = await self.repo.add_message(message_before)

        # Check that method returned created rocord's data
        assert message_after.id > 0
        assert message_after.dt is not None
        assert message_after.chat_id == message_before.chat_id
        assert message_after.text == message_before.text
        assert message_after.sender_id == message_before.sender_id

        # Check that the record was persisted in the DB
        assert (await self._check_if_message_has_persisted(message_after.id)) is True

    async def test_add_notification(self):
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

        # Check that method returned created rocord's data
        assert notification_after.id > 0
        assert notification_after.dt is not None
        assert notification_after.chat_id == notification_before.chat_id
        assert notification_after.text == notification_before.text
        assert notification_after.params == notification_before.params

        # Check that the record was persisted in the DB
        assert (
            await self._check_if_message_has_persisted(notification_after.id)
        ) is True

    # Methods below should be implemented in the descendant class
    async def _check_if_chat_has_persisted(self, chat_id: uuid.UUID) -> bool:
        raise NotImplementedError()

    async def _check_if_message_has_persisted(self, message_id: int) -> bool:
        raise NotImplementedError()

    async def _check_if_user_chat_link_has_persisted(
        self, user_id: uuid.UUID, chat_id: uuid.UUID
    ) -> bool:
        raise NotImplementedError()
