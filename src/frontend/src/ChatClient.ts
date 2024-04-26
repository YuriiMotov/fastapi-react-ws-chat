import {ConstantBackoff, Websocket, WebsocketBuilder} from "websocket-ts";


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
    messages: string[];
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

type SetState<ValueType> = React.Dispatch<React.SetStateAction<ValueType>>;


class ChatClient {
    #connection: Websocket | null = null;
    #userId: string | null = null;
    #lastPacketId: number = 0
    #selectedChat: ChatDataExtended | null = null;
    #chatList: ChatDataExtended[] = [];

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
            this.#requestChatMessageList(chat.id);
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
        this.#requestJoinedChatList();
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
                const messagesEncoded = (srv_p.data as ChatMessagesResponsePacket).messages;
                const messages = messagesEncoded.map((m)=>JSON.parse(m));
                console.log(`RespGetMessages has been received: ${srv_p.data}, ${messages}`);
                this.#setSelectedChatMessages([...messages]);
                break;
            case 'SrvEventList':
                console.log(`SrvEventList has been received: ${srv_p.data}`);
                const chatEventsPacket = srv_p.data as ChatEventListPacket;
                for (const chatEvent of chatEventsPacket.events) {
                    switch (chatEvent.event_type) {
                        case "ChatMessageEvent":
                            console.log(`ChatMessageEvent has been received: ${chatEvent}`);
                            const chatMessageEvent = chatEvent as ChatMessageEvent;
                            if (this.#selectedChat && (chatMessageEvent.message.chat_id === this.#selectedChat.id)){
                                this.#setSelectedChatMessages(prev=>[chatMessageEvent.message, ...prev]);
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
                console.log(`Unknown server packet ${srv_p}.`);
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

    #requestChatMessageList(chatId: string) {
        if (this.#connection) {
            const cmd = {
                "id": (this.#lastPacketId += 1),
                "data": {
                    "packet_type": "CMDGetMessages",
                    "chat_id": chatId
                }
            };
            this.#connection.send(JSON.stringify(cmd));
        } else {
            console.log("Attempt to call requestChatMessageList while disconnected")
        };

    }
}

export {ChatClient, ChatDataExtended, ChatMessage};
