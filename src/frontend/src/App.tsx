import React from "react";
import { useState, useEffect, useRef } from "react";
import { ChatClient, ChatDataExtended, ChatMessage } from "./ChatClient";
import { ChatListComponent } from "./ChatUI/ChatList";

import { Grid, GridItem } from "@chakra-ui/react";
import { ChatComponent, ChatComponentRef } from "./ChatUI/Chat";
import { ServiceButtonsBlockCompnent } from "./ChatUI/ServiceButtonsBlockCompnent";

function App() {
  const [clientId, setClientId] = useState("-");
  const [reconnectCount, setReconnectCount] = useState(0);
  const [chatList, setChatList] = useState<ChatDataExtended[]>([]);
  const [selectedChat, setSelectedChat] = useState<ChatDataExtended | null>(
    null
  );
  const [selectedChatMessages, setSelectedChatMessages] = useState<
    ChatMessage[]
  >([]);

  const chatClient = useRef<ChatClient>(
    new ChatClient(
      setChatList,
      setSelectedChat,
      setChatMessageListStoreScrollPos
    )
  );
  const connectDelay = useRef<number | null>(null);

  const chatComponentRef = useRef<ChatComponentRef>(null);

  // Connect to WS on user change
  useEffect(() => {
    if (clientId.length > 1) {
      connectDelay.current = setTimeout(() => {
        chatClient.current.connect(clientId);
      }, 100);
    }
    return () => {
      if (connectDelay.current) {
        clearTimeout(connectDelay.current);
      }
      chatClient.current.disconnect();
    };
  }, [clientId, reconnectCount]);


  function setChatMessageListStoreScrollPos(messages: ChatMessage[]) {
    chatComponentRef.current?.onBeforMessageListChangeCallback();
    setSelectedChatMessages(messages);
  }

  return (
    <Grid
      h="calc(100vh)"
      templateRows="1fc"
      templateColumns="250px 1fr 250px"
      backgroundColor="whitesmoke"
    >
      <GridItem p={4}>
        <ChatListComponent
          chatList={chatList}
          selectedChatId={selectedChat?.id}
          onChatSelect={chatClient.current.selectChat.bind(chatClient.current)}
        />
      </GridItem>

      <GridItem backgroundColor="AppWorkspace" p={4}>
        {selectedChat !== null && (
          <ChatComponent
            h="calc(100vh - 2rem)"
            chat={selectedChat}
            currentUserID={clientId}
            chatMessages={selectedChatMessages}
            onSendMessage={chatClient.current.sendMessage.bind(chatClient.current)}
            onEditMessage={chatClient.current.editMessage.bind(chatClient.current)}
            onLoadPrevMessagesClick={chatClient.current.loadPreviousMessages.bind(chatClient.current)}
            ref={chatComponentRef}
          />
        )}
      </GridItem>

      <GridItem p={4}>
        <ServiceButtonsBlockCompnent
          clientId={clientId}
          chatList={chatList}
          onAddUserToChat={chatClient.current.addUserToChat.bind(chatClient.current)}
          onSetClientId={setClientId}
          onIncReconnectCount={()=>setReconnectCount(prev=>prev+1)}
        />
      </GridItem>
    </Grid>
  );
}

export default App;
