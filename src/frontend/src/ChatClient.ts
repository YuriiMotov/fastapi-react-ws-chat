import {ConstantBackoff, Websocket, WebsocketBuilder} from "websocket-ts";
import React from 'react';


interface ServerPacketData {
    packet_type: "RespError" | "RespSuccessNoBody" | "RespGetJoinedChatList" | "RespGetMessages" | "SrvEventList" | "SrvRespError";
};


interface ServerPacket {
    request_packet_id: boolean | null;
    data: ServerPacketData;
};

interface ChatDataExtended {
    id: string;
    title: string;
    owner_id: string;
    last_message_text: string | null;
    members_count: number;
};

interface JoinedChatListPacket extends ServerPacketData {
    chats: ChatDataExtended[];
};

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
};

interface ChatEventListPacket extends ServerPacketData {
    events: ChatEventBase[];
}

interface ChatEventBase {
    event_type: string;
};

interface ChatMessageEvent extends ChatEventBase {
    message: ChatMessage;
};

interface ChatMessageEditedEvent extends ChatEventBase {
    message: ChatMessage;
};

interface ChatListUpdateEvent extends ChatEventBase {
    action_type: string;
    chat_data: ChatDataExtended
}

type SetState<ValueType> = React.Dispatch<React.SetStateAction<ValueType>>;

class ChatMessages {
    minMessageId: number = Infinity;
    maxMessageId: number = 0;
    messages: ChatMessage[] = [];
}


const chatMessageRequestLimit = 5;

class ChatClient {
    #connection: Websocket | null = null;
    #userId: string | null = null;
    #lastPacketId: number = 0
    #selectedChat: ChatDataExtended | null = null;
    #chatList: ChatDataExtended[] = [];
    #chatMessages: Map<string, ChatMessages>;

    #setChatList: SetState<ChatDataExtended[]>;
    #setSelectedChat: SetState<ChatDataExtended | null>;
    #setSelectedChatMessages: SetState<ChatMessage[]>;

    constructor(
        setChatList: SetState<ChatDataExtended[]>,
        setSelectedChat: SetState<ChatDataExtended | null>,
        setSelectedChatMessages: SetState<ChatMessage[]>,
    ) {
        this.#setChatList = setChatList;
        this.#setSelectedChat = setSelectedChat;
        this.#setSelectedChatMessages = setSelectedChatMessages;
        this.#chatMessages = new Map<string, ChatMessages>();
    };

    // ................................  Public methods ................................

    connect(userId: string): void {
        if (this.#connection) {
            console.log("Attempt to call connect() while already connected. Disconnect first")
            return
        }
        this.#userId = userId
        this.#connection = new WebsocketBuilder(`ws://127.0.0.1:8000/ws/chat?user_id=${userId}`)
            .onOpen(this.#connectedHandler.bind(this))
            .onClose(this.#disconnectedHandler.bind(this))
            .onError(this.#connectionErrorHandler.bind(this))
            .onMessage(this.#messageReceiveHandler.bind(this))
            // .onRetry((i, ev) => console.log("retry"))
            .withBackoff(new ConstantBackoff(1000))
            .build();
    };

    disconnect(): void {
        if (this.#connection) {
            this.#connection.close();
            this.#connection = null
        }
    }

    selectChat(chat: ChatDataExtended) {
        if (this.#chatList.indexOf(chat) > -1) {
            this.#selectedChat = chat;
            this.#setSelectedChat(chat);
            if (this.#chatMessages.has(chat.id)) {
                this.#setSelectedChatMessages(
                    [...this.#chatMessages.get(chat.id)!.messages]
                );
            } else {
                this.#setSelectedChatMessages([]);
                this.#requestChatMessageList(chat.id);
            };
        }
    }

    sendMessage(text: string, chatId: string): void {
        if (this.#connection) {
            const cmd = {
                "id": (this.#lastPacketId += 1),
                "data": {
                    "packet_type": "CMDSendMessage",
                    "message": {
                        "chat_id": chatId,
                        "text": text,
                        "sender_id": this.#userId
                    }
                }
            };
            this.#connection.send(JSON.stringify(cmd));
            console.log(`Sending message: ${JSON.stringify(cmd)}`);
        } else {
            console.log("Attempt to call sendMessage while disconnected")
        };
    }


    editMessage(messageId: string, newText: string): void {
        if (this.#connection) {
            const cmd = {
                "id": (this.#lastPacketId += 1),
                "data": {
                    "packet_type": "CMDEditMessage",
                    "message_id": messageId,
                    "text": newText,
                }
            };
            this.#connection.send(JSON.stringify(cmd));
            console.log(`Editing message: ${JSON.stringify(cmd)}`);
        } else {
            console.log("Attempt to call editMessage while disconnected")
        };
    }

    addUserToChat(userId: string, chatId: string) {
        if (this.#connection) {
            const cmd = {
                "id": (this.#lastPacketId += 1),
                "data": {
                    "packet_type": "CMDAddUserToChat",
                    "user_id": userId,
                    "chat_id": chatId,
                }
            };
            this.#connection.send(JSON.stringify(cmd));
            console.log(`Adding user to chat: ${JSON.stringify(cmd)}`);
        } else {
            console.log("Attempt to call addUserToChat while disconnected")
        };
    }

    loadPreviousMessages(chatId: string) {
        if (this.#chatMessages.has(chatId)) {
            this.#requestChatMessageList(chatId, this.#chatMessages.get(chatId)!.minMessageId);
        } else {
            console.log("Error: calling loadPreviousMessages before loading last messages");
        }
    }

    // ................................  Private methods ................................

    #acknowledgeEvents() {
        if (this.#connection) {
            const cmd = {
                "id": (this.#lastPacketId += 1),
                "data": {
                    "packet_type": "CMDAcknowledgeEvents",
                }
            };
            this.#connection.send(JSON.stringify(cmd));
            console.log('Acknowledging events');
        } else {
            console.log("Attempt to call acknowledgeEvents while disconnected")
        };
    }

    #connectedHandler(ws: Websocket, event: Event): void {
        console.log("Connected to WebSocket server");
        this.#chatMessages.clear();
        this.#requestJoinedChatList();
        if (this.#selectedChat)
            this.#requestChatMessageList(this.#selectedChat.id);
    };

    #disconnectedHandler(ws: Websocket, event: Event): void {
        console.log("Disconnected from WebSocket server");
    };

    #connectionErrorHandler(ws: Websocket, event: Event): void {
        console.log("Connection error: " + event);
    };

    #messageReceiveHandler(ws: Websocket, event: MessageEvent): void {
        const srv_p: ServerPacket = (JSON.parse(event.data) as ServerPacket);
        switch (srv_p.data.packet_type) {
            case 'RespGetJoinedChatList':
                const chatListPacket: JoinedChatListPacket = (srv_p.data as JoinedChatListPacket)
                console.log('List of chats has been received');
                this.#chatList = chatListPacket.chats;
                this.#setChatList([...chatListPacket.chats]);
                break;
            case 'RespGetMessages':
                const messages = (srv_p.data as ChatMessagesResponsePacket).messages;
                console.log(`RespGetMessages has been received: ${srv_p.data}, ${messages}`);
                if (messages.length > 0) {
                    const chatId = messages[0].chat_id;
                    this.#updateChatMessageListInternal(chatId, messages.slice().reverse());
                    const chatMessages: ChatMessage[] = this.#chatMessages.has(chatId) ? this.#chatMessages.get(chatId)!.messages : [];
                    if (this.#selectedChat && (chatId === this.#selectedChat.id)) {
                        this.#setSelectedChatMessages([...chatMessages]);
                    };
                }
                break;
            case 'SrvEventList':
                console.log(`SrvEventList has been received: ${srv_p.data}`);
                const chatEventsPacket = srv_p.data as ChatEventListPacket;
                for (const chatEvent of chatEventsPacket.events) {
                    switch (chatEvent.event_type) {
                        case "ChatListUpdate":
                            console.log(`ChatListUpdateEvent has been received: ${chatEvent}`);
                            const chatListUpdatePacket = chatEvent as ChatListUpdateEvent;
                            switch (chatListUpdatePacket.action_type) {
                                case "add":
                                    this.#setChatList(prev=>[...prev, chatListUpdatePacket.chat_data]);
                                    break;
                                // case "delete":
                                //     this.#setChatList(prev=>prev.filter(chat=>chat.id !== chatListUpdatePacket.chat_data.id));
                                //     break;
                                // case "update":
                                //     this.#setChatList(prev=>prev.map(chat=>(chat.id === chatListUpdatePacket.chat_data.id) ? chatListUpdatePacket.chat_data : chat));
                                //     break;
                                default:
                                    console.log(`ChatListUpdateEvent with action_type=${chatListUpdatePacket.action_type} is not supported yet`)
                                    break;
                            }
                            break;
                        case "ChatMessageEvent":
                            console.log(`ChatMessageEvent has been received: ${chatEvent}`);
                            const chatMessageEvent = chatEvent as ChatMessageEvent;
                            const chatId = chatMessageEvent.message.chat_id;
                            this.#updateChatMessageListInternal(chatId, [chatMessageEvent.message,]);
                            if (this.#selectedChat && (chatMessageEvent.message.chat_id === this.#selectedChat.id)){
                                this.#setSelectedChatMessages([...this.#chatMessages.get(chatId)!.messages]);
                            }
                            break;
                        case "ChatMessageEdited":
                            console.log(`ChatMessageEdited has been received: ${chatEvent}`);
                            const chatMessageEditedEvent = chatEvent as ChatMessageEditedEvent;
                            const chatMessages = this.#chatMessages.get(chatMessageEditedEvent.message.chat_id);
                            if (chatMessages) {
                                chatMessages.messages = chatMessages.messages.map((message)=>{
                                    return (message.id === chatMessageEditedEvent.message.id) ? chatMessageEditedEvent.message : message;
                                });
                                if (this.#selectedChat && (chatMessageEditedEvent.message.chat_id === this.#selectedChat.id)){
                                    this.#setSelectedChatMessages([...chatMessages.messages]);
                                };
                                if (parseInt(chatMessageEditedEvent.message.id) === chatMessages.maxMessageId) {
                                    this.#updateChatListOnLastMessageUpdate(chatMessageEditedEvent.message);
                                }
                            } else {
                                this.#requestChatMessageList(chatMessageEditedEvent.message.chat_id);   // This case hasn't tested yet !
                            }

                            break;
                        default:
                            console.log(`Unknown chat event ${chatEvent}.`);
                    };
                };
                this.#acknowledgeEvents();
                break;
            case 'RespSuccessNoBody':
                console.log('RespSuccessNoBody has been received');
                break;
            case 'SrvRespError':
                console.log(`SrvRespError has been received: ${srv_p.data}`);
                break;
            default:
                console.log(`Unknown server packet ${event.data}.`);
        };
    };

    #requestJoinedChatList(): void {
        if (this.#connection) {
            const cmd = {
                "id": (this.#lastPacketId += 1),
                "data": {
                    "packet_type": "CMDGetJoinedChats"
                }
            };
            this.#connection.send(JSON.stringify(cmd));
        } else {
            console.log("Attempt to call requestJoinedChatList while disconnected")
        };
    };

    #requestChatMessageList(chatId: string, startId: number | null = null, limit: number = chatMessageRequestLimit) {
        if (this.#connection) {
            const cmd = {
                "id": (this.#lastPacketId += 1),
                "data": {
                    "packet_type": "CMDGetMessages",
                    "chat_id": chatId,
                    "start_id": startId,
                    "limit": limit,
                }
            };
            this.#connection.send(JSON.stringify(cmd));
        } else {
            console.log("Attempt to call requestChatMessageList while disconnected")
        };
    }

    #updateChatMessageListInternal(chatId: string, messages: ChatMessage[]) {
        console.log(`updateChatMessageListInternal(${chatId})`);
        if (this.#chatMessages.has(chatId) === false) {
            this.#chatMessages.set(chatId, new ChatMessages());
        }
        const chatMessages: ChatMessages = this.#chatMessages.get(chatId)!;
        let minMessageId = Infinity;
        let maxMessageId = 0;

        messages.forEach(message=>{
            const messageId = parseInt(message.id);
            if (messageId < minMessageId) {
                minMessageId = messageId;
            }
            if (messageId > maxMessageId) {
                maxMessageId = messageId;
            }
        });

        if (maxMessageId < chatMessages.minMessageId) {
            chatMessages.messages.unshift(...messages);
        } else if (minMessageId  > chatMessages.maxMessageId) {
            chatMessages.messages.push(...messages);
            this.#updateChatListOnLastMessageUpdate(messages[0]);
        } else {
            console.log("Insert messages to the middle");
            chatMessages.messages.push(...messages);
            chatMessages.messages.sort((a, b)=> parseInt(a.id) - parseInt(b.id));
            console.log("updateChatMessageListInternal is quite slow in inserting messages in the middle of the list.");
            console.log("Consider refactoring to store ID's as a numbers instead of strings to make it faster");
        };
        if (chatMessages.maxMessageId < maxMessageId)
            chatMessages.maxMessageId = maxMessageId;
        if (chatMessages.minMessageId > minMessageId)
            chatMessages.minMessageId = minMessageId;

    };

    #updateChatListOnLastMessageUpdate(lastMessage: ChatMessage) {
        this.#chatList = this.#chatList.map(chat=>{
            return (chat.id == lastMessage.chat_id) ? {...chat, "last_message_text": lastMessage.text} : chat;
        })
        this.#setChatList([...this.#chatList]);
    }

}

export {ChatClient, ChatDataExtended, ChatMessage};
