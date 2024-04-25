import { useState, useEffect, useRef } from 'react'
import { ChatClient } from './ChatClient';
import React from 'react';

function App() {

  const [clientId, setClientId] = useState("ef376e46-db3b-4beb-8170-82940d849847");

  const chatClient = useRef<ChatClient>(new ChatClient());
  const connectDelay = useRef<number | null>(null);

  useEffect(
      () => {
          connectDelay.current = setTimeout(
            () => {
              chatClient.current.connect(clientId);
            }, 100
          )

          return () => {
            if (connectDelay.current) {
              clearTimeout(connectDelay.current);
            }
            chatClient.current.disconnect();
          };
      },
      [clientId,]
  );


  return (
      <div>
        Works!
      </div>
  )
}

export default App
