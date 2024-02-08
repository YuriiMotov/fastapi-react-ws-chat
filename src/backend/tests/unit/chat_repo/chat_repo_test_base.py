from typing import TypeVar
import uuid
from schemas.chat import ChatSchema
from services.chat_repo.chat_repo_interface import ChatRepo
from schemas.chat_message import (
    ChatNotificationCreateSchema,
    ChatUserMessageCreateSchema,
)

T = TypeVar("T", bound=ChatRepo)


class ChatRepoTestBase:
    repo: ChatRepo
    repo_class: type[ChatRepo] = ChatRepo

    async def test_add_chat(self):
        """
        Note: this test doesn't check that object was persisted
        """
        self.repo = self.repo_class()

        chat_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chat_before = ChatSchema(id=chat_id, title="my chat", owner_id=user_id)
        chat_after = await self.repo.add_chat(chat_before)
        await self.repo.commit()

        assert chat_before.id == chat_after.id
        assert chat_before.title == chat_after.title
        assert chat_before.owner_id == chat_after.owner_id

    async def test_add_message(self):
        self.repo = self.repo_class()

        # Getting repared to test
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
        await self.repo.commit()

        assert message_after.id == 1
        assert message_after.dt is not None
        assert message_after.chat_id == message_before.chat_id
        assert message_after.text == message_before.text
        assert message_after.sender_id == message_before.sender_id

        assert len(self.repo.data.messages) == 1

    async def test_add_notification(self):
        self.repo = self.repo_class()

        # Getting repared to test
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
        await self.repo.commit()

        assert notification_after.id == 1
        assert notification_after.dt is not None
        assert notification_after.chat_id == notification_before.chat_id
        assert notification_after.text == notification_before.text
        assert notification_after.params == notification_before.params

        assert len(self.repo.data.messages) == 1
