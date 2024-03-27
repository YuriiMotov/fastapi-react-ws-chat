import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.models.user_chat_state import UserChatState
from backend.schemas.chat_message import ChatUserMessageSchema
from backend.schemas.event import ChatMessageEvent
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.chat_manager.utils import channel_code


async def test_acknowledge_events__updates_user_chat_state(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    UserChatState is updated after evoking ChatManager.acknowledge_events()
    """
    user_id = event_broker_user_id_list[0]
    chat_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    channel = channel_code("chat", chat_id)

    # Create Chat, User, UserChatLink
    chat = Chat(id=chat_id, title="my chat", owner_id=user_id)
    user = User(id=user_id, name="user")
    user_chat_link = UserChatLink(chat_id=chat_id, user_id=user_id)
    async_session.add_all((chat, user, user_chat_link))
    await async_session.commit()

    # Subscribe user for events
    await chat_manager.subscribe_for_updates(user_id)

    # Post message to the channel
    message = ChatUserMessageSchema(
        id=1,
        dt=datetime.now(UTC),
        chat_id=chat_id,
        text="my message",
        sender_id=another_user_id,
    )
    await chat_manager.event_broker.post_event(
        channel=channel,
        event=ChatMessageEvent(message=message),
    )

    # Receive and acknowledge events
    events = await chat_manager.get_events(user_id)
    assert len(events) == 1
    assert isinstance(events[0], ChatMessageEvent)
    message_id = events[0].message.id
    await chat_manager.acknowledge_events(user_id)

    # Check that UserChatState data updated in the DB
    res = await async_session.scalars(
        select(UserChatState).where(UserChatState.user_id == user_id)
    )
    user_chat_state_list = list(res.all())
    assert len(user_chat_state_list) == 1
    assert user_chat_state_list[0].chat_id == chat_id
    assert user_chat_state_list[0].last_delivered == message_id
