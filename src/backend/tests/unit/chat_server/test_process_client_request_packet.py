import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.chat_message import ChatUserMessage
from backend.models.user_chat_link import UserChatLink
from backend.schemas import client_packet as cli_p
from backend.schemas import server_packet as srv_p
from backend.schemas.chat_message import (
    ChatUserMessageCreateSchema,
    ChatUserMessageSchema,
)
from backend.services.chat_manager.chat_manager import ChatManager
from backend.services.ws_chat_server import _process_ws_client_request_packet


async def test_process_ws_client_request_get_joined_chats(
    chat_manager: ChatManager, async_session: AsyncSession
):
    user_id = uuid.uuid4()
    chat_ids = [uuid.uuid4() for _ in range(3)]
    current_user_id = user_id

    for chat_id in chat_ids:
        async_session.add(Chat(id=chat_id, title="my chat", owner_id=current_user_id))
        async_session.add(UserChatLink(chat_id=chat_id, user_id=user_id))

    await async_session.commit()

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDGetJoinedChats(),
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespGetJoinedChatList) is True
    if isinstance(response.data, srv_p.SrvRespGetJoinedChatList):
        assert len(response.data.chats) == len(chat_ids)
        for chat in response.data.chats:
            assert chat.id in chat_ids


async def test_process_ws_client_request_add_user_to_chat(
    chat_manager: ChatManager, async_session: AsyncSession
):

    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    current_user_id = user_id

    async_session.add(Chat(id=chat_id, title="my chat", owner_id=current_user_id))
    await async_session.commit()

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000),
        data=cli_p.CMDAddUserToChat(chat_id=chat_id, user_id=user_id),
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespSucessNoBody) is True
    user_chat_link = await async_session.scalar(
        select(UserChatLink)
        .where(UserChatLink.chat_id == chat_id)
        .where(UserChatLink.user_id == user_id)
    )
    assert user_chat_link is not None
    assert isinstance(user_chat_link, UserChatLink)


async def test_process_ws_client_request_get_messages(
    chat_manager: ChatManager, async_session: AsyncSession
):

    user_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    current_user_id = user_id
    messages: list[ChatUserMessage] = []
    for _ in range(3):
        messages.append(
            ChatUserMessage(
                chat_id=chat_id, text=f"msg {uuid.uuid4()}", sender_id=another_user_id
            )
        )

    async_session.add(Chat(id=chat_id, title="my chat", owner_id=current_user_id))
    async_session.add_all(messages)

    await async_session.commit()

    request = cli_p.ClientPacket(
        id=random.randint(1, 10000), data=cli_p.CMDGetMessages(chat_id=chat_id)
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespGetMessages) is True
    if isinstance(response.data, srv_p.SrvRespGetMessages):
        resp_messages = response.data.messages
    assert len(resp_messages) == len(messages)
    expected_message_texts = {msg.text for msg in messages}
    for resp_msg in resp_messages:
        resp_msg_obj = ChatUserMessageSchema.model_validate_json(resp_msg)
        assert resp_msg_obj.text in expected_message_texts


async def test_process_ws_client_request_send_message(
    chat_manager: ChatManager, async_session: AsyncSession
):
    user_id = uuid.uuid4()
    chat_id = uuid.uuid4()
    current_user_id = user_id

    async_session.add(Chat(id=chat_id, title="my chat", owner_id=current_user_id))
    async_session.add(UserChatLink(chat_id=chat_id, user_id=user_id))
    await async_session.commit()

    message = ChatUserMessageCreateSchema(
        chat_id=chat_id, text="my message", sender_id=user_id
    )
    request = cli_p.ClientPacket(
        id=random.randint(1, 10000), data=cli_p.CMDSendMessage(message=message)
    )

    response = await _process_ws_client_request_packet(
        chat_manager=chat_manager, packet=request, current_user_id=current_user_id
    )

    assert isinstance(response.data, srv_p.SrvRespSucessNoBody) is True
    message_in_db = await async_session.scalar(
        select(ChatUserMessage)
        .where(ChatUserMessage.chat_id == chat_id)
        .where(ChatUserMessage.sender_id == user_id)
    )
    assert message_in_db is not None
    assert isinstance(message_in_db, ChatUserMessage)
