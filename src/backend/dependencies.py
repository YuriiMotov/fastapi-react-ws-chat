from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, WebSocket
from fastapi.requests import HTTPConnection
from fastapi.security import SecurityScopes
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.auth_setups import oauth2_scheme
from backend.database import async_session_maker
from backend.schemas.user import UserSchema
from backend.services.auth.abstract_auth import AbstractAuth
from backend.services.auth.auth_exc import (
    AuthBadRequestParametersError,
    AuthBadTokenError,
    AuthUnauthorizedError,
)
from backend.services.auth.internal_sqla_auth import InternalSQLAAuth
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.event_broker.abstract_event_broker import AbstractEventBroker
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker
from backend.services.uow.abstract_uow import AbstractUnitOfWork
from backend.services.uow.sqla_uow import SQLAlchemyUnitOfWork


async def sqla_sessionmaker_dep():
    return async_session_maker


async def sqla_session_dep(
    session_maker: Annotated[async_sessionmaker, Depends(sqla_sessionmaker_dep)],
) -> AsyncGenerator[AsyncSession, None]:
    async with session_maker() as session:
        yield session


async def uow_dep(
    session_maker: Annotated[async_sessionmaker, Depends(sqla_sessionmaker_dep)]
) -> AbstractUnitOfWork:
    return SQLAlchemyUnitOfWork(session_maker=session_maker)


async def get_auth_service(
    session_maker: Annotated[async_sessionmaker, Depends(sqla_sessionmaker_dep)],
) -> AbstractAuth:
    return InternalSQLAAuth(session_maker=session_maker)


async def get_current_user(
    connection: HTTPConnection,
    security_scopes: SecurityScopes,
    auth_service: Annotated[AbstractAuth, Depends(get_auth_service)],
    access_token: Annotated[str, Depends(oauth2_scheme)],
) -> UserSchema:

    try:
        access_token_decoded = await auth_service.validate_token(
            token=access_token, token_type="access", required_scopes=security_scopes
        )
        # return UserSchema(name="FakeName", id=uuid.UUID(access_token_decoded.sub))
        return await auth_service.get_current_user(access_token_decoded)
    except (AuthUnauthorizedError, AuthBadTokenError) as exc:
        if isinstance(connection, WebSocket):
            await connection.close()
        raise HTTPException(status_code=403, detail=exc.detail, headers=exc.headers)
    except AuthBadRequestParametersError as exc:
        if isinstance(connection, WebSocket):
            await connection.close()
        raise HTTPException(status_code=400, detail=exc.detail)


async def event_broker_dep(
    current_user: Annotated[UserSchema, Depends(get_current_user)]
) -> AsyncGenerator[AbstractEventBroker, None]:
    event_broker = InMemoryEventBroker()
    async with event_broker.session(current_user.id):
        yield event_broker


async def chat_manager_dep(
    uow: Annotated[AbstractUnitOfWork, Depends(uow_dep)],
    event_broker: Annotated[AbstractEventBroker, Depends(event_broker_dep)],
) -> ChatManager:
    return ChatManager(uow=uow, event_broker=event_broker)
