import uuid
from typing import Literal


def channel_code(ch_type: Literal["chat", "user"], id: uuid.UUID) -> str:
    return f"{ch_type}_{id}"
