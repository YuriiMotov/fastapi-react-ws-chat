// Server packets

import { ChatDataExtended, ChatMessage } from "./ChatDataTypes";

interface ServerPacketData {
    packet_type:
      | "RespError"
      | "RespSuccessNoBody"
      | "RespGetJoinedChatList"
      | "RespGetMessages"
      | "SrvEventList"
      | "SrvRespError";
  }

interface ServerPacket {
  request_packet_id: boolean | null;
  data: ServerPacketData;
}

interface JoinedChatListPacket extends ServerPacketData {
  chats: ChatDataExtended[];
}

interface ChatMessagesResponsePacket extends ServerPacketData {
  messages: ChatMessage[];
}

interface ChatEventListPacket extends ServerPacketData {
    events: ChatEventBase[];
  }


// Server Events

interface ChatEventBase {
    event_type: string;
  }

interface ChatMessageEvent extends ChatEventBase {
  message: ChatMessage;
}

interface ChatMessageEditedEvent extends ChatEventBase {
  message: ChatMessage;
}

interface ChatListUpdateEvent extends ChatEventBase {
  action_type: string;
  chat_data: ChatDataExtended;
}


export {
    ServerPacket,
    JoinedChatListPacket,
    ChatMessagesResponsePacket,
    ChatEventBase,
    ChatEventListPacket,
    ChatMessageEvent,
    ChatMessageEditedEvent,
    ChatListUpdateEvent,
};
