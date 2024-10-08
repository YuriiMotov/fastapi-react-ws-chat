import random
import uuid
from asyncio import sleep as asleep
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.testclient import TestClient, WebSocketTestSession

from backend.auth_setups import Scopes
from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.chat_message import ChatUserMessageCreateSchema
from backend.schemas.client_packet import (
    ClientPacket,
    CMDAddUserToChat,
    CMDGetJoinedChats,
    CMDGetMessages,
    CMDSendMessage,
)
from backend.schemas.event import ChatMessageEvent, UserAddedToChatNotification
from backend.schemas.server_packet import (
    SrvEventList,
    SrvRespError,
    SrvRespGetJoinedChatList,
    SrvRespGetMessages,
    SrvRespSucessNoBody,
)
from backend.services.chat_manager.chat_manager import (
    USER_JOINED_CHAT_NOTIFICATION,
    ChatManager,
)
from backend.services.chat_manager.chat_manager_exc import RepositoryError
from backend.services.chat_manager.utils import channel_code
from backend.services.event_broker.in_memory_event_broker import InMemoryEventBroker
from backend.tests.unit.endpoints.helpers import (
    connect_and_perform_request,
    create_access_token,
    perform_request,
)

# ---------------------------------------------------------------------------------
# Tests for websocket connect\disconnect


async def test_ws_chat_connect(client: TestClient, registered_user_data: dict):
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    with client.websocket_connect(f"/ws/chat?access_token={access_token}"):
        await asleep(0.1)


async def test_ws_chat_subscribe_on_connect(
    client: TestClient, event_broker: InMemoryEventBroker, registered_user_data: dict
):
    user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    mocked_subscribe = AsyncMock(wraps=event_broker.subscribe_list)
    with patch.object(InMemoryEventBroker, "subscribe_list", new=mocked_subscribe):
        with client.websocket_connect(f"/ws/chat?access_token={access_token}"):
            await asleep(0.1)
            # Check that chat_manager.event_broker.subscribe_list() was called
            mocked_subscribe.assert_awaited_with(
                user_id=user_id, channels=[channel_code("user", user_id)]
            )


async def test_ws_chat_unsubscribe_on_connection_close(
    client: TestClient, event_broker: InMemoryEventBroker, registered_user_data: dict
):
    user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    with client.websocket_connect(f"/ws/chat?access_token={access_token}"):
        await asleep(0.1)
        assert str(user_id) in event_broker._subscribers
    # Check that EventBroker's session data was deleted for this call
    assert str(user_id) not in event_broker._subscribers


# ---------------------------------------------------------------------------------
# Tests for CMDGetJoinedChats command


async def test_ws_chat_get_joined_chats__success(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    owner_id = uuid.uuid4()
    # Create chats, add user to chats
    chat_ids = [uuid.uuid4() for _ in range(3)]
    for chat_id in chat_ids:
        async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
        async_session.add(UserChatLink(chat_id=chat_id, user_id=current_user_id))
    await async_session.commit()

    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespGetJoinedChatList)
    if isinstance(srv_packet.data, SrvRespGetJoinedChatList):
        assert len(srv_packet.data.chats) == len(chat_ids)


def test_ws_chat_get_joined_chats__empty_list(
    client: TestClient, registered_user_data: dict
):
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespGetJoinedChatList)
    if isinstance(srv_packet.data, SrvRespGetJoinedChatList):
        assert len(srv_packet.data.chats) == 0


def test_ws_chat_get_joined_chats__error(
    client: TestClient, registered_user_data: dict
):
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    cmd = CMDGetJoinedChats()
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    raise_error = RepositoryError(detail="repo error")
    with patch.object(
        ChatManager,
        "get_joined_chat_list",
        new=Mock(side_effect=raise_error),
    ):
        srv_packet = connect_and_perform_request(
            client, f"/ws/chat?access_token={access_token}", client_packet
        )
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespError)
        if isinstance(srv_packet.data, SrvRespError):
            assert srv_packet.data.error_data.error_code == raise_error.error_code
            assert srv_packet.data.error_data.detail == raise_error.detail


# ---------------------------------------------------------------------------------
# Tests for CMDAddUserToChat command


async def test_ws_chat_add_user_to_chat__success(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    owner_id = current_user_id
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    # Create chat and user
    another_user = User(id=another_user_id, name=f"user_{another_user_id.hex[:5]}")
    chat = Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id)
    async_session.add_all([another_user, chat])
    await async_session.commit()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=another_user_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespSucessNoBody)


async def test_ws_chat_add_user_to_chat__chat_doesnt_exist_error(
    client: TestClient, registered_user_data: dict
):
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=another_user_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespError)
    if isinstance(srv_packet.data, SrvRespError):
        assert srv_packet.data.error_data.error_code == "BAD_REQUEST"
        assert (
            srv_packet.data.error_data.detail == f"Chat with ID={chat_id} doesn't exist"
        )


async def test_ws_chat_add_user_to_chat__unauthorized_error(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    owner_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    # Create chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    await async_session.commit()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=another_user_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespError)
    if isinstance(srv_packet.data, SrvRespError):
        assert srv_packet.data.error_data.error_code == "UNAUTHORIZED_ACTION"
        assert "unauthorized to add users to" in srv_packet.data.error_data.detail


# ---------------------------------------------------------------------------------
# Tests for CMDSendMessage command


async def test_ws_chat_send_message__success(
    client: TestClient,
    async_session_maker: async_sessionmaker,
    registered_user_data: dict,
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    owner_id = current_user_id
    chat_id = uuid.uuid4()
    # Create chat, add user to chat
    async with async_session_maker() as async_session:
        async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
        async_session.add(UserChatLink(chat_id=chat_id, user_id=current_user_id))
        await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=current_user_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespSucessNoBody)

    # await asyncio.sleep(0.5)

    async with async_session_maker() as async_session:
        message_db = await async_session.scalar(
            select(ChatUserMessage)
            .where(ChatUserMessage.chat_id == chat_id)
            .where(ChatUserMessage.sender_id == current_user_id)
        )
        assert message_db is not None
        # assert message_db.text == message.text


async def test_ws_chat_send_message__unauthorized_error(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    owner_id = current_user_id
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    # Create chat, add user to chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=current_user_id))
    await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=another_user_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespError)
    if isinstance(srv_packet.data, SrvRespError):
        assert srv_packet.data.error_data.error_code == "UNAUTHORIZED_ACTION"
        assert (
            "Can't send message on behalf of another user"
            in srv_packet.data.error_data.detail
        )

    message_db = await async_session.scalar(
        select(ChatUserMessage)
        .where(ChatUserMessage.chat_id == chat_id)
        .where(ChatUserMessage.sender_id == current_user_id)
    )
    assert message_db is None


async def test_ws_chat_send_message__unauthorized_not_chat_member_error(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    owner_id = current_user_id
    chat_id = uuid.uuid4()
    # Create chat
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=current_user_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespError)
    if isinstance(srv_packet.data, SrvRespError):
        assert srv_packet.data.error_data.error_code == "UNAUTHORIZED_ACTION"
        assert "is not a member of chat" in srv_packet.data.error_data.detail

    message_db = await async_session.scalar(
        select(ChatUserMessage)
        .where(ChatUserMessage.chat_id == chat_id)
        .where(ChatUserMessage.sender_id == current_user_id)
    )
    assert message_db is None


# ---------------------------------------------------------------------------------
# Tests for CMDGetMessages command


async def test_ws_chat_get_messages__success(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    chat_id = uuid.uuid4()
    # Create user, chat, user-chat link, messages
    messages = [
        ChatUserMessage(
            chat_id=chat_id, text=f"message {uuid.uuid4()}", sender_id=current_user_id
        )
        for _ in range(3)
    ]
    chat = Chat(id=chat_id, title="chat", owner_id=current_user_id)
    user_chat = UserChatLink(user_id=current_user_id, chat_id=chat_id)
    async_session.add_all((chat, user_chat, *messages))
    await async_session.commit()

    expected_messages = list(reversed(messages))
    cmd = CMDGetMessages(chat_id=chat_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespGetMessages)
    if isinstance(srv_packet.data, SrvRespGetMessages):
        assert len(srv_packet.data.messages) == len(messages)
        for i in range(len(messages)):
            assert srv_packet.data.messages[i].text == expected_messages[i].text


@pytest.mark.xfail()
async def test_ws_chat_get_messages__success_empty_list(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    chat_id = uuid.uuid4()
    # Create user, chat, user-chat link
    chat = Chat(id=chat_id, title="chat", owner_id=current_user_id)
    user_chat = UserChatLink(user_id=current_user_id, chat_id=chat_id)
    async_session.add_all((chat, user_chat))
    await async_session.commit()

    cmd = CMDGetMessages(chat_id=chat_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    srv_packet = connect_and_perform_request(
        client, f"/ws/chat?access_token={access_token}", client_packet
    )
    assert srv_packet.request_packet_id == client_packet.id
    assert isinstance(srv_packet.data, SrvRespGetMessages)
    if isinstance(srv_packet.data, SrvRespGetMessages):
        assert len(srv_packet.data.messages) == 0


async def test_ws_chat_get_messages__error(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    current_user_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    chat_id = uuid.uuid4()
    # Create user, chat, user-chat link
    chat = Chat(id=chat_id, title="chat", owner_id=current_user_id)
    user_chat = UserChatLink(user_id=current_user_id, chat_id=chat_id)
    async_session.add_all((chat, user_chat))
    await async_session.commit()

    cmd = CMDGetMessages(chat_id=chat_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    raise_error = RepositoryError(detail="repo error")
    with patch.object(
        ChatManager,
        "get_message_list",
        new=Mock(side_effect=raise_error),
    ):
        srv_packet = connect_and_perform_request(
            client, f"/ws/chat?access_token={access_token}", client_packet
        )
        assert srv_packet.request_packet_id == client_packet.id
        assert isinstance(srv_packet.data, SrvRespError)
        if isinstance(srv_packet.data, SrvRespError):
            assert srv_packet.data.error_data.error_code == raise_error.error_code
            assert srv_packet.data.error_data.detail == raise_error.detail


# ---------------------------------------------------------------------------------
# Test receiving events


async def test_ws_chat_receive_events__user_message(
    client: TestClient,
    async_session: AsyncSession,
    registered_user_data: dict,
    registered_user_data_2: dict,
):
    user1_id = uuid.UUID(registered_user_data["id"])
    user2_id = uuid.UUID(registered_user_data_2["id"])
    access_token_1 = create_access_token(registered_user_data, [Scopes.chat_user])
    access_token_2 = create_access_token(registered_user_data_2, [Scopes.chat_user])
    # Add user1 and user2 to chat
    owner_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user1_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user2_id))
    await async_session.commit()

    # Send message from user1 to chat. Check that both users receive events
    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text=f"my message {uuid.uuid4()}", sender_id=user1_id
    )
    cmd = CMDSendMessage(message=message)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    user1_websocket: WebSocketTestSession
    user2_websocket: WebSocketTestSession

    with (
        client.websocket_connect(
            f"/ws/chat?access_token={access_token_1}"
        ) as user1_websocket,
        client.websocket_connect(
            f"/ws/chat?access_token={access_token_2}"
        ) as user2_websocket,
    ):
        srv_packet = perform_request(user1_websocket, client_packet)
        assert isinstance(srv_packet.data, SrvRespSucessNoBody)  # Msg was sent
        await asleep(0.1)

        # Receive user1's events
        srv_packet = perform_request(user1_websocket, None)
        assert isinstance(srv_packet.data, SrvEventList)
        if isinstance(srv_packet.data, SrvEventList):
            assert len(srv_packet.data.events) == 1
            event = srv_packet.data.events[0]
            assert isinstance(event, ChatMessageEvent)
            if isinstance(event, ChatMessageEvent):
                assert event.message.text == message.text

        # Receive user2's events
        srv_packet = perform_request(user2_websocket, None)
        assert isinstance(srv_packet.data, SrvEventList)
        if isinstance(srv_packet.data, SrvEventList):
            assert len(srv_packet.data.events) == 1
            event = srv_packet.data.events[0]
            assert isinstance(event, ChatMessageEvent)
            if isinstance(event, ChatMessageEvent):
                assert event.message.text == message.text


async def test_ws_chat_receive_events__user_added_to_chat_message(
    client: TestClient, async_session: AsyncSession, registered_user_data: dict
):
    user1_id = uuid.UUID(registered_user_data["id"])
    access_token = create_access_token(registered_user_data, [Scopes.chat_user])
    user2_id = uuid.uuid4()
    owner_id = user1_id
    chat_id = uuid.uuid4()
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user1_id))
    async_session.add(User(id=user2_id, name="user 2"))
    await async_session.commit()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=user2_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    user1_websocket: WebSocketTestSession
    with client.websocket_connect(
        f"/ws/chat?access_token={access_token}"
    ) as user1_websocket:
        srv_packet = perform_request(user1_websocket, client_packet)
        assert isinstance(srv_packet.data, SrvRespSucessNoBody)  # User was added
        await asleep(0.1)

        # Receive user1's events
        srv_packet = perform_request(user1_websocket, None)
        assert isinstance(srv_packet.data, SrvEventList)
        if isinstance(srv_packet.data, SrvEventList):
            assert len(srv_packet.data.events) == 1
            event = srv_packet.data.events[0]
            assert isinstance(event, ChatMessageEvent)
            if isinstance(event, ChatMessageEvent):
                assert event.message.text == USER_JOINED_CHAT_NOTIFICATION


@pytest.mark.xfail(reason="Fails sometimes. Investigate")
async def test_ws_chat_receive_events__user_added_to_chat_notification(
    client: TestClient, async_session: AsyncSession
):
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    owner_id = user1_id
    chat_id = uuid.uuid4()
    async_session.add(Chat(id=chat_id, title=f"chat {chat_id}", owner_id=owner_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user1_id))
    await async_session.commit()

    cmd = CMDAddUserToChat(chat_id=chat_id, user_id=user2_id)
    client_packet = ClientPacket(id=random.randint(1, 1000), data=cmd)
    user1_websocket: WebSocketTestSession
    user2_websocket: WebSocketTestSession
    with (
        client.websocket_connect(f"/ws/chat?user_id={user1_id}") as user1_websocket,
        client.websocket_connect(f"/ws/chat?user_id={user2_id}") as user2_websocket,
    ):
        srv_packet = perform_request(user1_websocket, client_packet)
        assert isinstance(srv_packet.data, SrvRespSucessNoBody)  # User was added
        await asleep(0.1)

        # Receive user2's events
        srv_packet = perform_request(user2_websocket, None)
        assert isinstance(srv_packet.data, SrvEventList)
        if isinstance(srv_packet.data, SrvEventList):
            assert len(srv_packet.data.events) == 1
            event = srv_packet.data.events[0]
            assert isinstance(event, UserAddedToChatNotification)
            if isinstance(event, UserAddedToChatNotification):
                assert event.chat_id == chat_id
