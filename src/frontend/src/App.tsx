import React from "react";
import { useState, useEffect, useRef } from "react";
import { ChatClient } from "./ChatClient";
import { ChatDataExtended, ChatMessage } from "./ChatDataTypes";
import { ChatListComponent } from "./ChatUI/ChatList";

import { Grid, GridItem } from "@chakra-ui/react";
import { ChatComponent, ChatComponentRef } from "./ChatUI/Chat";
import { ServiceButtonsBlockCompnent } from "./ChatUI/ServiceButtonsBlockCompnent";
import { LoginFormComponent } from "./ChatUI/LoginForm";

function ChatApp() {
  const [accessToken, setAccessToken] = useState("-");
  const [refreshToken, setRefreshToken] = useState("");
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
  const connectDelay = useRef<NodeJS.Timeout | null>(null);

  const chatComponentRef = useRef<ChatComponentRef>(null);

  // Connect to WS on user change
  useEffect(() => {
    if (accessToken.length > 1) {
      connectDelay.current = setTimeout(() => {
        chatClient.current.connect(accessToken);
      }, 100);
    }
    return () => {
      if (connectDelay.current) {
        clearTimeout(connectDelay.current);
      }
      chatClient.current.disconnect();
    };
  }, [accessToken, reconnectCount]);


  function setChatMessageListStoreScrollPos(messages: ChatMessage[]) {
    chatComponentRef.current?.onBeforMessageListChangeCallback();
    setSelectedChatMessages(messages);
  }

  function setTokens(accessToken: string, refreshToken: string): void {
    setAccessToken(accessToken);
    setRefreshToken(refreshToken);
  }


  return (
    <>
      { (accessToken.length > 1) ? (
        <Grid
          h="calc(100vh)"
          templateRows="1fc"
          templateColumns="250px 1fr 250px"
          backgroundColor="whitesmoke"
        >
          <GridItem p={4}>
            <ChatListComponent
              chatList={chatList}
              selectedChatID={selectedChat?.id}
              onChatSelect={chatClient.current.selectChat.bind(chatClient.current)}
            />
          </GridItem>

          <GridItem backgroundColor="AppWorkspace" p={4}>
            {selectedChat !== null && (
              <ChatComponent
                h="calc(100vh - 2rem)"
                chat={selectedChat}
                currentUserID={accessToken}
                chatMessages={selectedChatMessages}
                onSendMessage={chatClient.current.sendMessage.bind(chatClient.current)}
                onEditMessage={chatClient.current.editMessage.bind(chatClient.current)}
                onLoadPrevMessagesClick={
                  chatClient.current.loadPreviousMessages.bind(chatClient.current)
                }
                ref={chatComponentRef}
              />
            )}
          </GridItem>

          <GridItem p={4}>
            <ServiceButtonsBlockCompnent
              clientID={accessToken}
              chatList={chatList}
              onAddUserToChat={chatClient.current.addUserToChat.bind(chatClient.current)}
              onSetClientID={setAccessToken}
              onIncReconnectCount={()=>setReconnectCount(prev=>prev+1)}
            />
          </GridItem>
        </Grid>
      ) : (
        // <Text >huhuhuh</Text>
        <LoginFormComponent setTokens={setTokens} />
      )}
    </>
  );
}

export default ChatApp;
