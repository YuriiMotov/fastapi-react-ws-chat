import { ConstantBackoff, Websocket, WebsocketBuilder } from "websocket-ts";
import { jwtDecode } from "jwt-decode";
import React from "react";
import { ChatData, ChatDataExtended, ChatMessage, User } from "./ChatDataTypes";
import {
  ChatEventBase,
  ChatEventListPacket,
  ChatListUpdateEvent,
  ChatMessageEditedEvent,
  ChatMessageEvent,
  ChatMessagesResponsePacket,
  FirstCircleListUpdateEvent,
  JoinedChatListPacket,
  ServerPacket,
  UserAutocompleteResponsePacket,
} from "./ChatProtocolTypes";

type SetState<ValueType> = React.Dispatch<React.SetStateAction<ValueType>>;

class ChatMessages {
  minMessageID: number = Infinity;
  maxMessageID: number = 0;
  messages: ChatMessage[] = [];
}

const chatMessageRequestLimit = 5;

class ChatClient {
  #connection: Websocket | null = null;
  #accessToken: string | null = null;
  #user_id: string | null = null;
  #lastPacketID: number = 0;
  #selectedChat: ChatDataExtended | null = null;
  #chatList: ChatDataExtended[] = [];
  #chatMessages: Map<string, ChatMessages>;
  #userNamesCache: Map<string, string>;
  #lastUserAutocompleteInput: number = 0;

  #setClientID: SetState<string>;
  #setChatList: SetState<ChatDataExtended[]>;
  #setSelectedChat: SetState<ChatDataExtended | null>;
  #setSelectedChatMessages: (messages: ChatMessage[]) => void;
  #setUserAutocompleteResults: (users: User[]) => void;

  constructor(
    setClientID: SetState<string>,
    setChatList: SetState<ChatDataExtended[]>,
    setSelectedChat: SetState<ChatDataExtended | null>,
    setSelectedChatMessages: (messages: ChatMessage[]) => void,
    setUserAutocompleteResults: (users: User[]) => void,
  ) {
    this.#setClientID = setClientID;
    this.#setChatList = setChatList;
    this.#setSelectedChat = setSelectedChat;
    this.#setSelectedChatMessages = setSelectedChatMessages;
    this.#setUserAutocompleteResults = setUserAutocompleteResults;
    this.#chatMessages = new Map<string, ChatMessages>();
    this.#userNamesCache = new Map<string, string>();
  }

  // ................................  Public methods ................................

  connect(accessToken: string): void {
    if (this.#connection) {
      console.log(
        "Attempt to call connect() while already connected. Disconnect first"
      );
      return;
    }
    this.#accessToken = accessToken;
    const decoded_token = jwtDecode(accessToken);
    this.#user_id = fixUUID(decoded_token.sub!);
    this.#setClientID(this.#user_id);
    this.#connection = new WebsocketBuilder(
      `ws://127.0.0.1:8000/ws/chat?access_token=${accessToken}`
    )
      .onOpen(this.#connectedHandler.bind(this))
      .onClose(this.#disconnectedHandler.bind(this))
      .onError(this.#connectionErrorHandler.bind(this))
      .onMessage(this.#messageReceiveHandler.bind(this))
      // .onRetry((i, ev) => console.log("retry"))
      .withBackoff(new ConstantBackoff(1000))
      .build();
  }

  disconnect(): void {
    if (this.#connection) {
      this.#connection.close();
      this.#connection = null;
    }
  }

  selectChat(chat: ChatDataExtended) {
    if (this.#chatList.indexOf(chat) > -1) {
      this.#selectedChat = chat;
      this.#setSelectedChat(chat);
      if (this.#chatMessages.has(chat.id)) {
        this.#setSelectedChatMessages([
          ...this.#chatMessages.get(chat.id)!.messages,
        ]);
      } else {
        this.#setSelectedChatMessages([]);
        this.#requestChatMessageList(chat.id);
      }
    }
  }

  sendMessage(text: string, chatID: string): void {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDSendMessage",
          message: {
            chat_id: chatID,
            text: text,
            sender_id: this.#user_id,
          },
        },
      };
      this.#connection.send(JSON.stringify(cmd));
      console.log(`Sending message: ${JSON.stringify(cmd)}`);
    } else {
      console.log("Attempt to call sendMessage while disconnected");
    }
  }

  editMessage(messageID: string, newText: string): void {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDEditMessage",
          message_id: messageID,
          text: newText,
        },
      };
      this.#connection.send(JSON.stringify(cmd));
      console.log(`Editing message: ${JSON.stringify(cmd)}`);
    } else {
      console.log("Attempt to call editMessage while disconnected");
    }
  }

  addUserToChat(userID: string, chatID: string) {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDAddUserToChat",
          user_id: userID,
          chat_id: chatID,
        },
      };
      this.#connection.send(JSON.stringify(cmd));
      console.log(`Adding user to chat: ${JSON.stringify(cmd)}`);
    } else {
      console.log("Attempt to call addUserToChat while disconnected");
    }
  }

  loadPreviousMessages(chatID: string) {
    if (this.#chatMessages.has(chatID)) {
      this.#requestChatMessageList(
        chatID,
        this.#chatMessages.get(chatID)!.minMessageID
      );
    } else {
      console.log(
        "Error: calling loadPreviousMessages before loading last messages"
      );
    }
  }

  createChat(chat_info: ChatData) {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDCreateChat",
          chat_data: chat_info,
        },
      };
      this.#connection.send(JSON.stringify(cmd));
    } else {
      console.log("Attempt to call createChat while disconnected");
    }
  }

  getUserAutocomplete(inputText: string) {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDGetUserList",
          name_filter: inputText,
        },
      };
      this.#lastUserAutocompleteInput = cmd.id;
      this.#connection.send(JSON.stringify(cmd));
    } else {
      console.log("Attempt to call getUserAutocomplete while disconnected");
    }
  }

  // ................................  Private methods ................................

  #acknowledgeEvents() {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDAcknowledgeEvents",
        },
      };
      this.#connection.send(JSON.stringify(cmd));
      console.log("Acknowledging events");
    } else {
      console.log("Attempt to call acknowledgeEvents while disconnected");
    }
  }

  #connectedHandler(ws: Websocket, event: Event): void {
    console.log("Connected to WebSocket server");
    this.#chatMessages.clear();
    this.#requestJoinedChatList();
    this.#requestFirstCircleList();
    if (this.#selectedChat) this.#requestChatMessageList(this.#selectedChat.id);
  }

  #disconnectedHandler(ws: Websocket, event: Event): void {
    console.log("Disconnected from WebSocket server");
  }

  #connectionErrorHandler(ws: Websocket, event: Event): void {
    console.log("Connection error: " + event);
  }

  #messageReceiveHandler(ws: Websocket, event: MessageEvent): void {
    const srv_p: ServerPacket = JSON.parse(event.data) as ServerPacket;
    console.log(`${srv_p.data.packet_type} has been received: ${srv_p.data}`);

    switch (srv_p.data.packet_type) {
      case "RespGetJoinedChatList":
        const chatListPacket = srv_p.data as JoinedChatListPacket;
        this.#chatList = chatListPacket.chats;
        this.#setChatList([...chatListPacket.chats]);
        break;
      case "RespGetMessages":
        const messages = (srv_p.data as ChatMessagesResponsePacket).messages;
        if (messages.length > 0) {
          const chatID = messages[0].chat_id;
          this.#updateChatMessageListInternal(
            chatID,
            messages.slice().reverse()
          );
        }
        break;
      case "RespGetUserList":
        if (srv_p.request_packet_id == this.#lastUserAutocompleteInput) {
          const users = (srv_p.data as UserAutocompleteResponsePacket).users;
          this.#setUserAutocompleteResults(users);
        } else {
          console.debug("Outdated RespGetUserList received");
        }
        break;
      case "SrvEventList":
        const chatEventsPacket = srv_p.data as ChatEventListPacket;
        for (const chatEvent of chatEventsPacket.events)
          this.#processServerEventPacket(chatEvent);
        this.#acknowledgeEvents();
        break;
      case "RespSuccessNoBody":
        break;
      case "SrvRespError":
        // ToDo: add error processing
        break;
      default:
        console.log(`Unknown server packet ${event.data}.`);
    }
  }

  #processServerEventPacket(chatEvent: ChatEventBase) {
    switch (chatEvent.event_type) {
      case "ChatListUpdate": {
        const chatListUpdatePacket = chatEvent as ChatListUpdateEvent;
        switch (chatListUpdatePacket.action_type) {
          case "add":
            this.#chatList = [
              ...this.#chatList,
              chatListUpdatePacket.chat_data,
            ];
            this.#setChatList([...this.#chatList]);
            break;
          // case "delete":
          //     this.#setChatList(prev=>prev.filter(chat=>chat.id !== chatListUpdatePacket.chat_data.id));
          //     break;
          // case "update":
          //     this.#setChatList(prev=>prev.map(chat=>(chat.id === chatListUpdatePacket.chat_data.id) ? chatListUpdatePacket.chat_data : chat));
          //     break;
          default:
            console.log(
              `ChatListUpdateEvent with action_type=${chatListUpdatePacket.action_type} is not supported yet`
            );
            break;
        }
        break;
      }
      case "ChatMessageEvent": {
        const chatMessageEvent = chatEvent as ChatMessageEvent;
        const chatID = chatMessageEvent.message.chat_id;
        this.#updateChatMessageListInternal(chatID, [chatMessageEvent.message]);
        break;
      }
      case "ChatMessageEdited": {
        const chatMessageEditedEvent = chatEvent as ChatMessageEditedEvent;
        const editedMessage = chatMessageEditedEvent.message;
        const chatID = editedMessage.chat_id;
        const chatMessages = this.#chatMessages.get(chatID);
        this.#updateMessageSenderName(editedMessage);
        if (chatMessages) {
          chatMessages.messages = chatMessages.messages.map((message) => {
            return message.id === editedMessage.id ? editedMessage : message;
          });

          if (this.#selectedChat && chatID === this.#selectedChat.id)
            this.#setSelectedChatMessages([...chatMessages.messages]);

          const messageIDAsNum = parseInt(editedMessage.id);
          if (messageIDAsNum === chatMessages.maxMessageID) {
            this.#updateChatListOnLastMessageUpdate(editedMessage);
          }
        } else {
          console.log(
            "Chat message updated, but message list is empty. Request messages"
          );
          this.#requestChatMessageList(chatMessageEditedEvent.message.chat_id);
        }
        break;
      }
      case "FirstCircleUserListUpdate": {
        const firstCircleUpdateEvent = chatEvent as FirstCircleListUpdateEvent;
        if (firstCircleUpdateEvent.is_full)
          this.#userNamesCache.clear();
        for (let user of firstCircleUpdateEvent.users) {
          this.#userNamesCache.set(user.id, user.name);
        }
        break;
      }
      default:
        console.log(`Unknown chat event ${chatEvent}.`);
    }
  }

  #requestJoinedChatList(): void {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDGetJoinedChats",
        },
      };
      this.#connection.send(JSON.stringify(cmd));
    } else {
      console.log("Attempt to call requestJoinedChatList while disconnected");
    }
  }

  #requestFirstCircleList(): void {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDGetFirstCircleListUpdates",
        },
      };
      this.#connection.send(JSON.stringify(cmd));
    } else {
      console.log("Attempt to call requestFirstCircleList while disconnected");
    }
  }

  #requestChatMessageList(
    chatID: string,
    startID: number | null = null,
    limit: number = chatMessageRequestLimit
  ) {
    if (this.#connection) {
      const cmd = {
        id: (this.#lastPacketID += 1),
        data: {
          packet_type: "CMDGetMessages",
          chat_id: chatID,
          start_id: startID,
          limit: limit,
        },
      };
      this.#connection.send(JSON.stringify(cmd));
    } else {
      console.log("Attempt to call requestChatMessageList while disconnected");
    }
  }

  #updateChatMessageListInternal(chatID: string, messages: ChatMessage[]) {
    console.log(`updateChatMessageListInternal(${chatID})`);
    if (this.#chatMessages.has(chatID) === false) {
      this.#chatMessages.set(chatID, new ChatMessages());
    }
    const chatMessages: ChatMessages = this.#chatMessages.get(chatID)!;
    let minMessageID = Infinity;
    let maxMessageID = 0;
    let maxIDMessage: ChatMessage | null = null;

    messages.forEach((message) => {
      if (message.is_notification)
        message.text = this.#getNotificationText(message.text, message.params || "-")

      const messageID = parseInt(message.id);
      if (messageID < minMessageID) {
        minMessageID = messageID;
      }
      if (messageID > maxMessageID) {
        maxMessageID = messageID;
        maxIDMessage = message;
      }
    });

    if (maxMessageID < chatMessages.minMessageID) {
      chatMessages.messages.unshift(...messages);
    } else if (minMessageID > chatMessages.maxMessageID) {
      chatMessages.messages.push(...messages);
    } else {
      console.log("Insert messages to the middle");
      chatMessages.messages.push(...messages);
      chatMessages.messages.sort((a, b) => parseInt(a.id) - parseInt(b.id));
      console.log(
        "updateChatMessageListInternal is quite slow in inserting messages in the middle of the list."
      );
      console.log(
        "Consider refactoring to store ID's as a numbers instead of strings to make it faster"
      );
    }

    if (chatMessages.maxMessageID < maxMessageID) {
      if (maxIDMessage) this.#updateChatListOnLastMessageUpdate(maxIDMessage);
      chatMessages.maxMessageID = maxMessageID;
    }
    if (chatMessages.minMessageID > minMessageID)
      chatMessages.minMessageID = minMessageID;

    // update user names
    chatMessages.messages.forEach((message: ChatMessage) => {
      this.#updateMessageSenderName(message);
    });

    // Update message list in the UI if current chat's messages were changed
    if (this.#selectedChat && chatID === this.#selectedChat.id)
      this.#setSelectedChatMessages([...chatMessages.messages]);
  }

  #updateChatListOnLastMessageUpdate(lastMessage: ChatMessage) {
    this.#chatList = this.#chatList.map((chat) => {
      return chat.id == lastMessage.chat_id
        ? { ...chat, last_message_text: lastMessage.text }
        : chat;
    });
    this.#setChatList([...this.#chatList]);
  }

  #updateMessageSenderName(message: ChatMessage) {
    if (message.sender_id && !message.senderName)
      message.senderName = this.#userNamesCache.get(message.sender_id);
  }

  #getNotificationText(messageText: string, params: string): string {
    switch (messageText) {
      case "USER_JOINED_CHAT_MSG":
        const userName = this.#userNamesCache.get(params) || "Unknown user"
        return `${userName} joined chat`;
      default:
        return `Unknown event (${messageText})`;
    }
  }

}



function fixUUID(uuidString: string): string {
  return `${uuidString.substring(0, 8)}-${uuidString.substring(8, 12)}-${uuidString.substring(12, 16)}-${uuidString.substring(16, 20)}-${uuidString.substring(20)}`;
}






export { ChatClient };
