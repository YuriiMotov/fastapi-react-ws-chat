import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User


@pytest.mark.slow
async def test_updated_at(async_session: AsyncSession):
    user = User(id=uuid.uuid4(), name="user 1", hashed_password="")
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    created_at = user.updated_at

    await asyncio.sleep(1)  # Unfortunately freeze_time doesn't work here

    user.name = "new name"
    await async_session.commit()
    await async_session.refresh(user)
    assert user.updated_at > created_at
