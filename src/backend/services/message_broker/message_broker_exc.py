from dataclasses import dataclass


@dataclass(frozen=True)
class MessageBrokerException(Exception):
    detail: str = ""

    def __str__(self):
        return f"Error {self.__class__.__name__}: {self.detail}"


class MessageBrokerUserNotSubscribedError(MessageBrokerException):
    pass


class MessageBrokerFail(MessageBrokerException):
    pass
