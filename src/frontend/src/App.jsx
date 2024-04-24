import { useState, useEffect, useRef } from 'react'


function App() {

  const [clientId, setClientId] = useState("ef376e46-db3b-4beb-8170-82940d849847");

  const socket = useRef(null);
  const connectDelay = useRef(null);

  function requestChatList() {
    const cmd = {
      "id": 1,
      "data": {
        "packet_type": "CMDGetJoinedChats"
      }
    }
    socket.current.send(JSON.stringify(cmd))
  }


  useEffect(
      () => {
          connectDelay.current = setTimeout(
            () => {
              socket.current = new WebSocket(`ws://127.0.0.1:8000/ws/chat?user_id=${clientId}`);

              socket.current.onopen = function (event) {
                  console.log("Connected to WebSocket server");
              };

              socket.current.onerror = function (event) {
                console.log("Websocket connection error");
              };

              socket.current.onmessage = function (event) {
                const srv_p = JSON.parse(event.data);
                switch (srv_p.data.packet_type) {
                  case 'RespGetJoinedChatList':
                    console.log('List of chats:');
                    for (const chat of srv_p.data.chats) {
                      console.log(" - " + chat.title);
                    }
                    break;
                  default:
                    console.log(`Unknown server packet ${srv_p}.`);
                  console.log("Received message:", event);
                  };
              };
            }, 100
          )

          return () => {
            clearTimeout(connectDelay.current);
            if (socket.current) {
              socket.current.close();
              socket.current = null;
            }
          };
      },
      [clientId,]
  );


  return (
    <>
      <div>
        Works!
      </div>
      <button onClick={(e)=> {requestChatList()}}>Request chat list</button>
    </>
  )
}

export default App
