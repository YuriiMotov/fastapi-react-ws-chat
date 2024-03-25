import uuid
from datetime import datetime

from backend.schemas.chat_message import ChatUserMessageSchema
from backend.schemas.event import (
    AnyEvent,
    ChatMessageEvent,
    UserAddedToChatNotification,
)


def create_chat_event(event_class: type[AnyEvent]) -> AnyEvent:
    if event_class is ChatMessageEvent:
        return ChatMessageEvent(
            message=ChatUserMessageSchema(
                id=0,
                dt=datetime.now(),
                chat_id=uuid.uuid4(),
                text=f"message {uuid.uuid4()}",
                sender_id=uuid.uuid4(),
            )
        )
    if event_class is UserAddedToChatNotification:
        return UserAddedToChatNotification(chat_id=uuid.uuid4())

    raise Exception()
