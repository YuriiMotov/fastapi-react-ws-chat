from dataclasses import dataclass


@dataclass
class EventBrokerException(Exception):
    detail: str = ""

    def __str__(self):
        return f"Error {self.__class__.__name__}: {self.detail}"


class EventBrokerUserNotSubscribedError(EventBrokerException):
    pass


class EventBrokerFail(EventBrokerException):
    pass
