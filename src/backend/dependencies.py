from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.database import async_session_maker
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.message_broker.abstract_message_broker import (
    AbstractMessageBroker,
)
from backend.services.message_broker.in_memory_message_broker import (
    InMemoryMessageBroker,
)
from backend.services.uow.abstract_uow import AbstractUnitOfWork
from backend.services.uow.sqla_uow import SQLAlchemyUnitOfWork


def sqla_sessionmaker_dep():
    return async_session_maker


def uow_dep(
    async_session_maker: Annotated[async_sessionmaker, Depends(sqla_sessionmaker_dep)]
) -> AbstractUnitOfWork:
    return SQLAlchemyUnitOfWork(async_session_maker=async_session_maker)


def message_broker_dep() -> AbstractMessageBroker:
    return InMemoryMessageBroker()


def chat_manager_dep(
    uow: Annotated[AbstractUnitOfWork, Depends(uow_dep)],
    message_broker: Annotated[AbstractMessageBroker, Depends(message_broker_dep)],
) -> ChatManager:
    return ChatManager(uow=uow, message_broker=message_broker)
