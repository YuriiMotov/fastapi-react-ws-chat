import { ConstantBackoff, Websocket, WebsocketBuilder } from "websocket-ts";
import React from "react";

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

interface ChatDataExtended {
  id: string;
  title: string;
  owner_id: string;
  last_message_text: string | null;
  members_count: number;
}

interface JoinedChatListPacket extends ServerPacketData {
  chats: ChatDataExtended[];
}

interface ChatMessagesResponsePacket extends ServerPacketData {
  messages: ChatMessage[];
}

interface ChatMessage {
  id: string;
  chat_id: string;
  dt: string;
  text: string;
  is_notification: string;
  sender_id?: string;
  params?: string;
  senderName?: string;
}

interface ChatEventListPacket extends ServerPacketData {
  events: ChatEventBase[];
}

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

type SetState<ValueType> = React.Dispatch<React.SetStateAction<ValueType>>;

class ChatMessages {
  minMessageID: number = Infinity;
  maxMessageID: number = 0;
  messages: ChatMessage[] = [];
}

const chatMessageRequestLimit = 5;

class ChatClient {
  #connection: Websocket | null = null;
  #userID: string | null = null;
  #lastPacketID: number = 0;
  #selectedChat: ChatDataExtended | null = null;
  #chatList: ChatDataExtended[] = [];
  #chatMessages: Map<string, ChatMessages>;
  #userNamesCache: Map<string, string>;

  #setChatList: SetState<ChatDataExtended[]>;
  #setSelectedChat: SetState<ChatDataExtended | null>;
  #setSelectedChatMessages: (messages: ChatMessage[]) => void;

  constructor(
    setChatList: SetState<ChatDataExtended[]>,
    setSelectedChat: SetState<ChatDataExtended | null>,
    setSelectedChatMessages: (messages: ChatMessage[]) => void
  ) {
    this.#setChatList = setChatList;
    this.#setSelectedChat = setSelectedChat;
    this.#setSelectedChatMessages = setSelectedChatMessages;
    this.#chatMessages = new Map<string, ChatMessages>();
    this.#userNamesCache = new Map<string, string>();

    // Add some user names for tests
    this.#userNamesCache.set("ef376e46-db3b-4beb-8170-82940d849847", "John");
    this.#userNamesCache.set("ef376e56-db3b-4beb-8170-82940d849847", "Joe");
  }

  // ................................  Public methods ................................

  connect(userID: string): void {
    if (this.#connection) {
      console.log(
        "Attempt to call connect() while already connected. Disconnect first"
      );
      return;
    }
    this.#userID = userID;
    this.#connection = new WebsocketBuilder(
      `ws://127.0.0.1:8000/ws/chat?user_id=${userID}`
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
            sender_id: this.#userID,
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
    switch (srv_p.data.packet_type) {
      case "RespGetJoinedChatList":
        const chatListPacket: JoinedChatListPacket =
          srv_p.data as JoinedChatListPacket;
        console.log("List of chats has been received");
        this.#chatList = chatListPacket.chats;
        this.#setChatList([...chatListPacket.chats]);
        break;
      case "RespGetMessages":
        const messages = (srv_p.data as ChatMessagesResponsePacket).messages;
        console.log(
          `RespGetMessages has been received: ${srv_p.data}, ${messages}`
        );
        if (messages.length > 0) {
          const chatID = messages[0].chat_id;
          this.#updateChatMessageListInternal(
            chatID,
            messages.slice().reverse()
          );
          const chatMessages: ChatMessage[] =
            this.#chatMessages.get(chatID)?.messages || [];
          if (this.#selectedChat && chatID === this.#selectedChat.id) {
            this.#setSelectedChatMessages([...chatMessages]);
          }
        }
        break;
      case "SrvEventList":
        console.log(`SrvEventList has been received: ${srv_p.data}`);
        const chatEventsPacket = srv_p.data as ChatEventListPacket;
        for (const chatEvent of chatEventsPacket.events) {
          switch (chatEvent.event_type) {
            case "ChatListUpdate":
              console.log(
                `ChatListUpdateEvent has been received: ${chatEvent}`
              );
              const chatListUpdatePacket = chatEvent as ChatListUpdateEvent;
              switch (chatListUpdatePacket.action_type) {
                case "add":
                  this.#chatList = [
                    ...this.#chatList,
                    chatListUpdatePacket.chat_data,
                  ];
                  this.#setChatList((prev) => [...this.#chatList]);
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
            case "ChatMessageEvent":
              console.log(`ChatMessageEvent has been received: ${chatEvent}`);
              const chatMessageEvent = chatEvent as ChatMessageEvent;
              const chatID = chatMessageEvent.message.chat_id;
              this.#updateChatMessageListInternal(chatID, [
                chatMessageEvent.message,
              ]);
              if (
                this.#selectedChat &&
                chatMessageEvent.message.chat_id === this.#selectedChat.id
              ) {
                this.#setSelectedChatMessages([
                  ...this.#chatMessages.get(chatID)!.messages,
                ]);
              }
              break;
            case "ChatMessageEdited":
              console.log(`ChatMessageEdited has been received: ${chatEvent}`);
              const chatMessageEditedEvent =
                chatEvent as ChatMessageEditedEvent;
              this.#updateMessageSenderName(chatMessageEditedEvent.message);
              const chatMessages = this.#chatMessages.get(
                chatMessageEditedEvent.message.chat_id
              );
              if (chatMessages) {
                chatMessages.messages = chatMessages.messages.map((message) => {
                  return message.id === chatMessageEditedEvent.message.id
                    ? chatMessageEditedEvent.message
                    : message;
                });
                if (
                  this.#selectedChat &&
                  chatMessageEditedEvent.message.chat_id ===
                    this.#selectedChat.id
                ) {
                  this.#setSelectedChatMessages([...chatMessages.messages]);
                }
                if (
                  parseInt(chatMessageEditedEvent.message.id) ===
                  chatMessages.maxMessageID
                ) {
                  this.#updateChatListOnLastMessageUpdate(
                    chatMessageEditedEvent.message
                  );
                }
              } else {
                console.log(
                  "Chat message updated, but message list is empty. Request messages"
                );
                this.#requestChatMessageList(
                  chatMessageEditedEvent.message.chat_id
                ); // This case hasn't tested yet !
              }

              break;
            default:
              console.log(`Unknown chat event ${chatEvent}.`);
          }
        }
        this.#acknowledgeEvents();
        break;
      case "RespSuccessNoBody":
        console.log("RespSuccessNoBody has been received");
        break;
      case "SrvRespError":
        console.log(`SrvRespError has been received: ${srv_p.data}`);
        break;
      default:
        console.log(`Unknown server packet ${event.data}.`);
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

}


export { ChatClient, ChatDataExtended, ChatMessage };
