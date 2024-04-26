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



type SetState<ValueType> = React.Dispatch<React.SetStateAction<ValueType>>;



class ChatClient {
    #connection: Websocket | null = null;
    #userId: string | null = null;
    #setChatList: SetState<ChatDataExtended[]>;
    #setSelectedChat: SetState<ChatDataExtended | null>;
    #chatList: ChatDataExtended[] = [];

    constructor(
        setChatList: SetState<ChatDataExtended[]>,
        setSelectedChat: SetState<ChatDataExtended | null>
    ) {
        this.#setChatList = setChatList;
        this.#setSelectedChat = setSelectedChat;
    };

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
            .onReconnect(this.#reconnectedHandler)
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
            this.#setSelectedChat(chat);
        }
    }

    sendMessage(text: string, chatId: string): void {
        if (this.#connection) {
            const cmd = {
                "id": 1,
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


    #reconnectedHandler(ws: Websocket, event: Event): void {
        console.log("Reconnected to WebSocket server");
        this.#requestJoinedChatList();
    };


    #messageReceiveHandler(ws: Websocket, event: MessageEvent): void {
        const srv_p: ServerPacket = (JSON.parse(event.data) as ServerPacket);
        switch (srv_p.data.packet_type) {
            case 'RespGetJoinedChatList':
                const chatListPacket: JoinedChatListPacket = (srv_p.data as JoinedChatListPacket)
                console.log('List of chats:');
                for (const chat of chatListPacket.chats) {
                    console.log(" - " + chat.title);
                }
                this.#chatList = chatListPacket.chats;
                this.#setChatList([...chatListPacket.chats]);
                break;

            case 'SrvEventList':
                console.log(`SrvEventList received: ${srv_p.data}`);
                break;
            case 'RespSuccessNoBody':
                console.log('RespSuccessNoBody received');
                break;
            case 'SrvRespError':
                console.log(`SrvRespError received: ${srv_p.data}`);
                break;
            default:
                console.log(`Unknown server packet ${srv_p}.`);
        };

    };

    #requestJoinedChatList(): void {
        if (this.#connection) {
            const cmd = {
                "id": 1,
                "data": {
                    "packet_type": "CMDGetJoinedChats"
                }
            };
            this.#connection.send(JSON.stringify(cmd));
        } else {
            console.log("Attempt to call requestJoinedChatList while disconnected")
        };
    };
}

export {ChatClient, ChatDataExtended};
