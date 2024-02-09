from dataclasses import dataclass


@dataclass(frozen=True)
class ChatManagerException(Exception):
    error_code: str = "CHAT_MANAGER_GENERAL_ERROR"
    detail: str = ""

    def __str__(self):
        return f"Error {self.error_code}: {self.detail}"


class UnauthorizedAction(ChatManagerException):
    error_code: str = "UNAUTHORIZED_ACTION"
