from dataclasses import dataclass


@dataclass
class AuthException(Exception):
    detail: str = ""

    def __str__(self):
        return f"Error {self.__class__.__name__}: {self.detail}"


class AuthBadRequestParametersError(AuthException):
    pass


class AuthBadCredentialsError(AuthBadRequestParametersError):
    pass


@dataclass
class AuthBadTokenError(AuthBadRequestParametersError):
    headers: dict[str, str] | None = None


@dataclass
class AuthUnauthorizedError(AuthException):
    headers: dict[str, str] | None = None
