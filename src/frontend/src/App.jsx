import { useState, useEffect, useRef } from 'react'


function App() {

  const [clientId, setClientId] = useState("ef376e46-db3b-4beb-8170-82940d849847");

  const socket = useRef(null);
  const connectDelay = useRef(null);

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
                  console.log("Received message:", event);
                  setMessage((oldArray) => [...oldArray, event.data]);
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
    </>
  )
}

export default App
