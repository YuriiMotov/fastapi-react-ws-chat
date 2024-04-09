from abc import ABC, abstractmethod

from backend.services.chat_repo.abstract_chat_repo import AbstractChatRepo

USE_AS_CONTEXT_MANAGER_ERROR = "UoW should be used as a context manager"


class AbstractUnitOfWork(ABC):
    chat_repo: AbstractChatRepo

    @abstractmethod
    async def __aenter__(self):
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args):
        raise NotImplementedError

    @abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError
