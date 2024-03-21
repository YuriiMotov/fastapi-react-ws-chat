from dataclasses import dataclass


@dataclass()
class ChatManagerException(Exception):
    detail: str
    error_code: str = "CHAT_MANAGER_GENERAL_ERROR"

    def __str__(self):
        return f"Error {self.error_code}: {self.detail}"


@dataclass()
class UnauthorizedAction(ChatManagerException):
    error_code: str = "UNAUTHORIZED_ACTION"


@dataclass()
class RepositoryError(ChatManagerException):
    error_code: str = "REPOSITORY_ERROR"


@dataclass()
class EventBrokerError(ChatManagerException):
    error_code: str = "EVENT_BROKER_ERROR"


@dataclass()
class NotSubscribedError(ChatManagerException):
    error_code: str = "USER_NOT_SUBSCRIBED"


@dataclass()
class BadRequest(ChatManagerException):
    error_code: str = "BAD_REQUEST"
