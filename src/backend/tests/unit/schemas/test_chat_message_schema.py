from datetime import datetime
import uuid

from pydantic import TypeAdapter

from schemas.chat_message import (
    ChatNotificationSchema,
    ChatUserMessageSchema,
    ChatMessageAny,
    AnnotatedChatMessageAny,
)


def test_validate_user_message():
    json_data = {
        "id": 1,
        "chat_id": uuid.uuid4(),
        "text": "message text",
        "dt": datetime.utcnow(),
        "sender_id": uuid.uuid4(),
        "is_notification": False,
    }

    message_adapter: TypeAdapter[ChatMessageAny] = TypeAdapter(
        AnnotatedChatMessageAny  # type: ignore
    )

    message = message_adapter.validate_python(json_data)

    assert isinstance(message, ChatUserMessageSchema) is True
    if isinstance(message, ChatUserMessageSchema):
        assert message.sender_id == json_data["sender_id"]


def test_validate_notification():
    json_data = {
        "id": 1,
        "chat_id": uuid.uuid4(),
        "text": "message text",
        "params": str(uuid.uuid4()),
        "dt": datetime.utcnow(),
        "is_notification": True,
    }

    message_adapter: TypeAdapter[ChatMessageAny] = TypeAdapter(
        AnnotatedChatMessageAny  # type: ignore
    )

    message = message_adapter.validate_python(json_data)

    assert isinstance(message, ChatNotificationSchema) is True
