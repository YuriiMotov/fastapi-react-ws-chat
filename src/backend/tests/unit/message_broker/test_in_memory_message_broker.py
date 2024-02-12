import uuid
from typing import cast

import pytest

from services.message_broker.in_memory_message_broker import InMemoryMessageBroker
from tests.unit.message_broker.message_broker_test_base import MessageBrokerTestBase


class TestInMemoryMessageBroker(MessageBrokerTestBase):

    @pytest.fixture(autouse=True)
    def _create_message_broker(self):
        self.message_broker = InMemoryMessageBroker()

    async def _check_subscribed(self, user_id: uuid.UUID, channel: str) -> bool:
        message_broker = cast(InMemoryMessageBroker, self.message_broker)
        return str(user_id) in message_broker._subscribtions[channel]

    async def _get_messages(self, user_id: uuid.UUID) -> list[str]:
        message_broker = cast(InMemoryMessageBroker, self.message_broker)
        return list(message_broker._message_queue[str(user_id)])
