import React from "react";
import { useState, useEffect, useRef } from "react";
import { ChatClient } from "./ChatClient";
import { ChatData, ChatDataExtended, ChatMessage, User } from "./ChatDataTypes";
import { ChatListComponent } from "./ChatUI/ChatList";

import { Grid, GridItem } from "@chakra-ui/react";
import { ChatComponent, ChatComponentRef } from "./ChatUI/Chat";
import { ServiceButtonsBlockCompnent } from "./ChatUI/ServiceButtonsBlockCompnent";
import { LoginFormComponent } from "./ChatUI/LoginForm";
import { ChatCreateComponent, ChatCreateComponentRef } from "./ChatUI/ChatCreate";

function ChatApp() {
  const [accessToken, setAccessToken] = useState("-");
  const [clientID, setClientID] = useState("-");
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
      setClientID,
      setChatList,
      setSelectedChat,
      setChatMessageListStoreScrollPos,
      setUserAutocompleteResult,
    )
  );
  const connectDelay = useRef<NodeJS.Timeout | null>(null);

  const chatComponentRef = useRef<ChatComponentRef>(null);
  const chatCreateComponentRef = useRef<ChatCreateComponentRef>(null);

  function onUserAutocomplete(inputText: string) {
    chatClient.current.getUserAutocomplete(inputText);
  }

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

  function createChat(chat_info: ChatData) {
    chatClient.current.createChat(chat_info=chat_info);
  }

  function createChatWindowShow() {
    if (chatCreateComponentRef.current)
      chatCreateComponentRef.current.show();
  }

  function setUserAutocompleteResult(users: User[]) {
    chatComponentRef.current?.onSetUserAutocomplete(users);
  }

  return (
    <>
      { (clientID.length > 1) ? (
      <>
        <ChatCreateComponent currentUserID={clientID} onSubmit={createChat} ref={chatCreateComponentRef} />
        <Grid
          h="calc(100vh)"
          templateRows="1fc"
          templateColumns="250px 1fr 250px"
          backgroundColor="whitesmoke"
        >
          <GridItem p={4} overflow="scroll">
            <ChatListComponent
              chatList={chatList}
              selectedChatID={selectedChat?.id}
              onChatSelect={chatClient.current.selectChat.bind(chatClient.current)}
              onChatCreateClick={createChatWindowShow}
            />
          </GridItem>

          <GridItem backgroundColor="AppWorkspace" p={4}>
            {selectedChat !== null && (
              <ChatComponent
                h="calc(100vh - 2rem)"
                chat={selectedChat}
                currentUserID={clientID}
                chatMessages={selectedChatMessages}
                onSendMessage={chatClient.current.sendMessage.bind(chatClient.current)}
                onEditMessage={chatClient.current.editMessage.bind(chatClient.current)}
                onLoadPrevMessagesClick={
                  chatClient.current.loadPreviousMessages.bind(chatClient.current)
                }
                onUserAutocompleteRequest={onUserAutocomplete}
                onAddUserToChatRequest={chatClient.current.addUserToChat.bind(chatClient.current)}
                ref={chatComponentRef}
              />
            )}
          </GridItem>

          <GridItem p={4}>
            <ServiceButtonsBlockCompnent
              clientID={clientID}
              chatList={chatList}
              onAddUserToChat={chatClient.current.addUserToChat.bind(chatClient.current)}
              onIncReconnectCount={()=>setReconnectCount(prev=>prev+1)}
            />
          </GridItem>
        </Grid>
      </>
      ) : (
        <LoginFormComponent setTokens={setTokens} />
      )}
    </>
  );
}

export default ChatApp;
