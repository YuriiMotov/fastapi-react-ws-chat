import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.chat import Chat
from backend.models.user import User
from backend.models.user_chat_link import UserChatLink
from backend.schemas.event import FirstCircleUserListUpdate
from backend.services.chat_manager.chat_manager import ChatManager

# Update on joining new chat


async def test_first_circle_updates_events__join_new_chat(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    After user joins a new chat, it should receive the FirstCircleUserListUpdate event
    with the list of users, that are added to their first circle.
    """
    # Create Users and Chat, ChatUserMessage, subscribe user for updates
    chat_owner_id = event_broker_user_id_list[0]
    user_1_id = event_broker_user_id_list[1]
    chat = Chat(id=uuid.uuid4(), title="", owner_id=chat_owner_id)
    user_1 = User(id=user_1_id, name="Me")
    user_2 = User(id=uuid.uuid4(), name="User 2")
    user_2_chat_link = UserChatLink(user_id=user_2.id, chat_id=chat.id)
    async_session.add_all((user_1, user_2, chat, user_2_chat_link))
    await async_session.commit()

    # Subscribe user to events
    await chat_manager.subscribe_for_updates(current_user_id=user_1_id)

    # Get list of users in the first circle (should be empty)
    first_circle = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1_id
    )
    assert len(first_circle) == 0

    # Join the chat where user_2 is a member
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_1.id, chat_id=chat.id
    )

    # Check that joining a chat triggers sending FirstCircleUserListUpdate
    # event (user_1 and user_2 in the list)
    events = await chat_manager.get_events(current_user_id=user_1_id)
    assert len(events) > 0
    for event in events:
        if isinstance(event, FirstCircleUserListUpdate):
            assert False, "FirstCircleUserListUpdate should be in the second list"
    await chat_manager.acknowledge_events(current_user_id=user_1_id)

    events = await chat_manager.get_events(current_user_id=user_1_id)
    assert len(events) > 0
    for event in events:
        if isinstance(event, FirstCircleUserListUpdate):
            assert event.is_full is False
            assert len(event.users) == 2
            assert event.users[0].id in (user_1.id, user_2.id)
            assert event.users[1].id in (user_1.id, user_2.id)
            assert event.users[0].id != event.users[1].id
            break
    else:
        assert False, "No FirstCircleUserListUpdate received"


async def test_first_circle_updates_events__join_new_chat_no_new_users(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    If user joins new chat, but there are no any new users in that chat (all of them
    are already in the first circle), FirstCircleUserListUpdate event shouldn't be sent
    """
    # Create Users and Chat, ChatUserMessage, subscribe user for updates
    chat_owner_id = event_broker_user_id_list[0]
    user_1_id = event_broker_user_id_list[1]
    chat_1 = Chat(id=uuid.uuid4(), title="", owner_id=chat_owner_id)
    chat_2 = Chat(id=uuid.uuid4(), title="", owner_id=chat_owner_id)
    user_1 = User(id=user_1_id, name="Me")
    user_2 = User(id=uuid.uuid4(), name="User 2")
    user_1_chat_1_link = UserChatLink(user_id=user_1.id, chat_id=chat_1.id)
    user_2_chat_1_link = UserChatLink(user_id=user_2.id, chat_id=chat_1.id)
    user_2_chat_2_link = UserChatLink(user_id=user_2.id, chat_id=chat_2.id)
    async_session.add_all(
        (
            user_1,
            user_2,
            chat_1,
            chat_2,
            user_1_chat_1_link,
            user_2_chat_1_link,
            user_2_chat_2_link,
        )
    )
    await async_session.commit()

    # Subscribe user to events
    await chat_manager.subscribe_for_updates(current_user_id=user_1_id)

    # Get list of users in the first circle (should be 2 users)
    first_circle = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1_id
    )
    assert len(first_circle) == 2

    # Join the chat_2
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_1.id, chat_id=chat_2.id
    )

    # Check that joining a chat where all the users are already in the first circle
    # doesn't trigger sending FirstCircleUserListUpdate
    for pass_no in range(2):
        events = await chat_manager.get_events(current_user_id=user_1_id)
        assert len(events) > 0
        for event in events:
            if isinstance(event, FirstCircleUserListUpdate):
                assert (
                    False
                ), f"FirstCircleUserListUpdate should NOT be in the list ({pass_no})"
        await chat_manager.acknowledge_events(current_user_id=user_1_id)


async def test_first_circle_updates_events__new_user_joined_mutual_chat(
    async_session: AsyncSession,
    chat_manager: ChatManager,
    event_broker_user_id_list: list[uuid.UUID],
):
    """
    After another user joins mutual chat, current user should receive the
    FirstCircleUserListUpdate event with the list of users, that are added to
    their first circle.
    """
    # Create Users and Chat, ChatUserMessage, subscribe user for updates
    chat_owner_id = event_broker_user_id_list[0]
    user_1_id = event_broker_user_id_list[1]
    chat = Chat(id=uuid.uuid4(), title="", owner_id=chat_owner_id)
    user_1 = User(id=user_1_id, name="Me")
    user_2 = User(id=uuid.uuid4(), name="User 2")
    user_chat_link = UserChatLink(user_id=user_1_id, chat_id=chat.id)
    async_session.add_all((user_1, user_2, chat, user_chat_link))
    await async_session.commit()

    # Subscribe user to events
    await chat_manager.subscribe_for_updates(current_user_id=user_1_id)

    # Get list of users in the first circle (should be only that user itself)
    first_circle = await chat_manager._get_first_circle_user_list_updates(
        current_user_id=user_1_id
    )
    assert len(first_circle) == 1
    assert first_circle[0].id == user_1_id

    # Receive and acknowledge all the events in the queue
    events = await chat_manager.get_events(current_user_id=user_1_id)
    await chat_manager.acknowledge_events(current_user_id=user_1_id)

    # Add user_2 to the chat
    await chat_manager.add_user_to_chat(
        current_user_id=chat_owner_id, user_id=user_2.id, chat_id=chat.id
    )

    # Check that adding the new user to mutual chat triggered sending
    # FirstCircleUserListUpdate event (user_2 was added to the list)
    events = await chat_manager.get_events(current_user_id=user_1_id)
    assert len(events) > 0
    for event in events:
        if isinstance(event, FirstCircleUserListUpdate):
            assert False, "FirstCircleUserListUpdate should be in the second list"
    await chat_manager.acknowledge_events(current_user_id=user_1_id)

    events = await chat_manager.get_events(current_user_id=user_1_id)
    assert len(events) > 0
    for event in events:
        if isinstance(event, FirstCircleUserListUpdate):
            assert event.is_full is False
            assert len(event.users) == 1
            assert event.users[0].id == user_2.id
            break
    else:
        assert False, "No FirstCircleUserListUpdate received"


# TODO: Add test for sending FirstCircleUserListUpdate on user update
