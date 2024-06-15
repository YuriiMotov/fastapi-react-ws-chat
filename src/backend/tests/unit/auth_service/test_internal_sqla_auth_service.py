import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.auth_setups import Scopes, pwd_context
from backend.models.user import User
from backend.services.auth.internal_sqla_auth import InternalSQLAAuth
from backend.tests.unit.auth_service.auth_service_test_base import AuthServiceTestBase


class TestInternalSQLAAuth(AuthServiceTestBase):

    @pytest.fixture()
    def auth_service(self, async_session_maker: async_sessionmaker):
        yield InternalSQLAAuth(session_maker=async_session_maker)

    @pytest.fixture()
    async def user_data(self, async_session: AsyncSession):
        password = str(uuid.uuid4())
        user_data = {
            "id": uuid.uuid4().hex,
            "name": f"User_{uuid.uuid4()}",
            "password": password,
            "scope": " ".join([e.value for e in Scopes]),
        }
        hashed_password = pwd_context.hash(password)
        user = User(
            id=uuid.UUID(user_data["id"]),
            name=user_data["name"],
            hashed_password=hashed_password,
            scope=user_data["scope"],
        )
        async_session.add(user)
        await async_session.commit()
        yield user_data
