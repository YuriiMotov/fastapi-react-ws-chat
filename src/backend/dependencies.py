import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.database import async_session_maker
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.event_broker.abstract_event_broker import AbstractEventBroker
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker
from backend.services.uow.abstract_uow import AbstractUnitOfWork
from backend.services.uow.sqla_uow import SQLAlchemyUnitOfWork


def sqla_sessionmaker_dep():
    return async_session_maker


def uow_dep(
    async_session_maker: Annotated[async_sessionmaker, Depends(sqla_sessionmaker_dep)]
) -> AbstractUnitOfWork:
    return SQLAlchemyUnitOfWork(async_session_maker=async_session_maker)


def event_broker_dep() -> AbstractEventBroker:
    return InMemoryEventBroker()


def chat_manager_dep(
    uow: Annotated[AbstractUnitOfWork, Depends(uow_dep)],
    event_broker: Annotated[AbstractEventBroker, Depends(event_broker_dep)],
) -> ChatManager:
    return ChatManager(uow=uow, event_broker=event_broker)


def get_current_user(user_id: uuid.UUID):
    return user_id
