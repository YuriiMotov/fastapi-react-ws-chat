from abc import ABC, abstractmethod

from backend.services.chat_repo.abstract_chat_repo import AbstractChatRepo


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
