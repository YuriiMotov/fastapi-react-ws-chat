"""
ChatUserMessageSchema and ChatNotificationSchema models are implemented using
disciminated unions.
(docs.pydantic.dev/latest/concepts/unions/#discriminated-unions-with-str-discriminators)

This allows you to automatically recognize the model during model validation.

Here is a list of tests that check whether it works as expected.

"""

import uuid
from datetime import UTC, datetime

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
        "dt": datetime.now(UTC),
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


def test_validate_notification__params_dict():
    """
    Validate data that is ChatNotificationSchema object (is_notification=True).
    `params` is dictionary
    """
    json_data = {
        "id": 1,
        "chat_id": uuid.uuid4(),
        "text": "message text",
        "params": {"user_name": "user name"},
        "dt": datetime.now(UTC),
        "is_notification": True,
    }

    message_adapter: TypeAdapter[ChatMessageAny] = TypeAdapter(
        AnnotatedChatMessageAny  # type: ignore
    )

    message = message_adapter.validate_python(json_data)

    assert isinstance(message, ChatNotificationSchema) is True


def test_validate_notification__params_str():
    """
    Validate data that is ChatNotificationSchema object (is_notification=True).
    `params` is string
    """
    json_data = {
        "id": 1,
        "chat_id": uuid.uuid4(),
        "text": "message text",
        "params": '{"user_name": "user name"}',
        "dt": datetime.now(UTC),
        "is_notification": True,
    }

    message_adapter: TypeAdapter[ChatMessageAny] = TypeAdapter(
        AnnotatedChatMessageAny  # type: ignore
    )

    message = message_adapter.validate_python(json_data)

    assert isinstance(message, ChatNotificationSchema) is True
