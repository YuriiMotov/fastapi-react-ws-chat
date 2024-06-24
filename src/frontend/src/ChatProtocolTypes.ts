// Server packets

import { ChatDataExtended, ChatMessage, User } from "./ChatDataTypes";

interface ServerPacketData {
    packet_type:
      | "RespError"
      | "RespSuccessNoBody"
      | "RespGetJoinedChatList"
      | "RespGetMessages"
      | "SrvEventList"
      | "SrvRespError"
      | "RespGetUserList";
  }

interface ServerPacket {
  request_packet_id: number | null;
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

interface UserAutocompleteResponsePacket extends ServerPacketData {
  users: User[];
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

interface FirstCircleListUpdateEvent extends ChatEventBase {
  users: User[];
  is_full: boolean;
}


export {
    ServerPacket,
    JoinedChatListPacket,
    ChatMessagesResponsePacket,
    ChatEventBase,
    ChatEventListPacket,
    UserAutocompleteResponsePacket,
    ChatMessageEvent,
    ChatMessageEditedEvent,
    ChatListUpdateEvent,
    FirstCircleListUpdateEvent,
};
