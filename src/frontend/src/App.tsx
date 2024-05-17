import React from "react";
import { useState, useEffect, useRef } from "react";
import { ChatClient, ChatDataExtended, ChatMessage } from "./ChatClient";
import { ChatListComponent } from "./ChatUI/ChatList";

import {
  Button,
  VStack,
  Grid,
  GridItem,
  Select,
} from "@chakra-ui/react";
import { ChatComponent, ChatComponentRef } from "./ChatUI/Chat";

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


  // Remember the scroll position before chat message list updating
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
        <VStack spacing="3">
          <Select
            placeholder="Select option"
            onChange={(e) => setClientId(e.target.value)}
          >
            <option value="-">-</option>
            <option value="ef376e46-db3b-4beb-8170-82940d849847">John</option>
            <option value="ef376e56-db3b-4beb-8170-82940d849847">Joe</option>
          </Select>
          {clientId === "ef376e46-db3b-4beb-8170-82940d849847" &&
            chatList.length < 4 && (
              <Button
                onClick={() =>
                  chatClient.current.addUserToChat(
                    clientId,
                    "eccf5b4a-c706-4c05-9ab2-5edc7539daad"
                  )
                }
              >
                Add yourself to forth chat
              </Button>
            )}
          {clientId === "ef376e46-db3b-4beb-8170-82940d849847" && (
            <Button
              onClick={() =>
                chatClient.current.addUserToChat(
                  "ef376e56-db3b-4beb-8170-82940d849847",
                  "eccf5b4a-c706-4c05-9ab2-5edc7539daad"
                )
              }
            >
              Add Joe to forth chat
            </Button>
          )}
          <Button onClick={() => setReconnectCount(reconnectCount + 1)}>
            Reconnect
          </Button>
        </VStack>
      </GridItem>
    </Grid>
  );
}

export default App;
