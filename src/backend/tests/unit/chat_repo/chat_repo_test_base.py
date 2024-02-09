from typing import TypeVar
import uuid
from schemas.chat import ChatSchema
from services.chat_repo.abstract_chat_repo import AbstractChatRepo
from schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
)

T = TypeVar("T", bound=AbstractChatRepo)


class ChatRepoTestBase:
    repo: AbstractChatRepo  # Should be initialized by fixture

    async def test_add_chat(self):
        """
        Note: this test doesn't check that object was persisted
        """

        # Getting prepared to test
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chat_before = ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        chat_after = await self.repo.add_chat(chat_before)

        assert chat_before.id == chat_after.id
        assert chat_before.title == chat_after.title
        assert chat_before.owner_id == chat_after.owner_id

        assert (await self._check_if_chat_has_persisted(chat_id)) is True

    async def test_add_message(self):
        # Getting prepared to test
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        )

        # Test
        message_before = ChatUserMessageCreateSchema(
            chat_id=chat_id, text="my message", sender_id=user_id
        )
        message_after = await self.repo.add_message(message_before)

        assert message_after.id == 1
        assert message_after.dt is not None
        assert message_after.chat_id == message_before.chat_id
        assert message_after.text == message_before.text
        assert message_after.sender_id == message_before.sender_id

        assert (await self._check_if_message_has_persisted(message_after.id)) is True

    async def test_add_notification(self):
        # Getting prepared to test
        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await self.repo.add_chat(
            ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        )

        # Test
        notification_before = ChatNotificationCreateSchema(
            chat_id=chat_id, text="notification", params=str(uuid.uuid4())
        )
        notification_after = await self.repo.add_notification(notification_before)

        assert notification_after.id == 1
        assert notification_after.dt is not None
        assert notification_after.chat_id == notification_before.chat_id
        assert notification_after.text == notification_before.text
        assert notification_after.params == notification_before.params

        assert (
            await self._check_if_message_has_persisted(notification_after.id)
        ) is True

    # Methods below should be implemented in concreet ChatRepoTest classes
    async def _check_if_chat_has_persisted(self, chat_id: uuid.UUID) -> bool:
        raise NotImplementedError()

    async def _check_if_message_has_persisted(self, message_id: uuid.UUID) -> bool:
        raise NotImplementedError()

    async def _check_if_user_chat_link_has_persisted(
        self, user_id: uuid.UUID, chat_id: uuid.UUID
    ) -> bool:
        raise NotImplementedError()
