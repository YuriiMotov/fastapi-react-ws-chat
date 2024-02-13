from dataclasses import dataclass


@dataclass(frozen=True)
class UnitOfWorkException(Exception):
    detail: str = ""

    def __str__(self):
        return f"Error {self.__class__.__name__}: {self.detail}"
