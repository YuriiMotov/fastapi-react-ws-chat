"""
ChatUserMessageSchema and ChatNotificationSchema models are implemented using
disciminated unions.
(docs.pydantic.dev/latest/concepts/unions/#discriminated-unions-with-str-discriminators)

This allows you to automatically recognize the model during model validation.

Here is a list of tests that check whether it works as expected.

"""

import uuid
from datetime import datetime

from pydantic import TypeAdapter

from backend.schemas.chat_message import (
    AnnotatedChatMessageAny,
    ChatMessageAny,
    ChatNotificationSchema,
    ChatUserMessageSchema,
)


def test_validate_user_message():
    """
    Validate data that is ChatUserMessageSchema object (is_notification=False)
    """
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
    """
    Validate data that is ChatNotificationSchema object (is_notification=True)
    """
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
