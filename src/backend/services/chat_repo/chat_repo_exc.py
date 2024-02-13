from dataclasses import dataclass


@dataclass(frozen=True)
class ChatRepoException(Exception):
    detail: str = ""

    def __str__(self):
        return f"Error {self.__class__.__name__}: {self.detail}"


class ChatRepoRequestError(ChatRepoException):
    pass


class ChatRepoDatabaseError(ChatRepoException):
    pass
