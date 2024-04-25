import {ConstantBackoff, Websocket, WebsocketBuilder} from "websocket-ts";


interface ServerPacketData {
    packet_type: "RespError" | "RespSuccessNoBody" | "RespGetJoinedChatList" | "RespGetMessages" | "SrvEventList";
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


class ChatClient {
    #connection: Websocket | null;

    constructor() {

    };

    connect(userId: string): void {
        if (this.#connection) {
            console.log("Attempt to call connect() while already connected. Disconnect first")
            return
        }
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

export {ChatClient};
