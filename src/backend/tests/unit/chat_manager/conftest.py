import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.user import User


@pytest.fixture(name="u_c")
async def users_and_chats(
    async_session: AsyncSession,
    event_broker_user_id_list: list[uuid.UUID],
):
    user_1 = User(id=event_broker_user_id_list[0], name="user 1", hashed_password="")
    user_2 = User(id=uuid.uuid4(), name="user 2", hashed_password="")
    user_3 = User(id=uuid.uuid4(), name="user 3", hashed_password="")
    chat_1 = Chat(id=uuid.uuid4(), title="chat 1", owner_id=user_1.id)
    chat_2 = Chat(id=uuid.uuid4(), title="chat 2", owner_id=user_1.id)
    async_session.add_all(
        [
            user_1,
            user_2,
            user_3,
            chat_1,
            chat_2,
        ]
    )
    await async_session.commit()
    return dict(
        user_1=user_1,
        user_2=user_2,
        user_3=user_3,
        chat_1=chat_1,
        chat_2=chat_2,
    )
