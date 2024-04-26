import { useState, useEffect, useRef } from 'react'
import { ChatClient, ChatDataExtended, ChatMessage } from './ChatClient';
import React from 'react';

function App() {

  const [clientId, setClientId] = useState("ef376e46-db3b-4beb-8170-82940d849847");
  const [chatList, setChatList] = useState<ChatDataExtended[]>([]);
  const [selectedChat, setSelectedChat] = useState<ChatDataExtended | null>(null);
  const [selectedChatMessages, setSelectedChatMessages] = useState<ChatMessage[]>([]);
  const [sendMessageText, setSendMessageText] = useState("");

  const chatClient = useRef<ChatClient>(new ChatClient(setChatList, setSelectedChat, setSelectedChatMessages));
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
        <h4>Chat list:</h4>
        <ul>
          {
            chatList.map((chat)=> (
              <li key={chat.id}>
                <button onClick={()=> chatClient.current.selectChat(chat)}>
                  {(selectedChat === chat) ? (<b>{chat.title}</b>) : chat.title}
                </button>
              </li>
            ))
          }
        </ul>
        {
          (selectedChat !== null) ? (
            <div>
              <input value={sendMessageText} onChange={(e)=>setSendMessageText(e.target.value)} />
              <button onClick={()=>chatClient.current.sendMessage(sendMessageText, selectedChat.id)}>Send</button>
            </div>
          ): (<b>Chat not selected</b>)
        }
        <ul>
          {
            selectedChatMessages.map((message) => (
              <li key={message.id}>{message.text}</li>
            ))
          }
        </ul>
      </div>
  )
}

export default App
