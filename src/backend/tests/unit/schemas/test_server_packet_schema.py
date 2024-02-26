import uuid
from datetime import datetime

from backend.schemas.chat_message import ChatUserMessageSchema
from backend.schemas.event import ChatMessageEvent
from backend.schemas.server_packet import ServerPacket, SrvEventList


def test_event_list_packet():

    msg = ChatUserMessageSchema(
        id=1,
        dt=datetime.utcnow(),
        chat_id=uuid.uuid4(),
        text="my msg",
        sender_id=uuid.uuid4(),
    )

    packet = ServerPacket(
        request_packet_id=None,
        data=SrvEventList(events=[ChatMessageEvent(message=msg)]),
    )

    packet_validated = ServerPacket.model_validate_json(packet.model_dump_json())

    assert isinstance(packet_validated.data, SrvEventList)
    if isinstance(packet_validated.data, SrvEventList):
        assert len(packet_validated.data.events) == 1
        event = packet_validated.data.events[0]
        assert isinstance(event, ChatMessageEvent)
        if isinstance(event, ChatMessageEvent):
            assert event.message.text == msg.text
