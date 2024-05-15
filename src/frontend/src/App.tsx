import React from "react";
import { useState, useEffect, useRef } from "react";
import { ChatClient, ChatDataExtended, ChatMessage } from "./ChatClient";
import { ChatListComponent } from "./ChatUI/ChatList";

import {
  Box,
  Button,
  Flex,
  VStack,
  Spacer,
  Grid,
  GridItem,
  Select,
} from "@chakra-ui/react";
import { MessageListComponent } from "./ChatUI/MessageList";
import { SendMessageComponent } from "./ChatUI/SendMessage";

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
  const messageListScrollElementID = useRef<string | null>(
    "chat-messages-bottom"
  );

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

  // Scroll message list container on message list update
  useEffect(() => {
    if (messageListScrollElementID.current) {
      const ele = document.querySelector(
        "#" + messageListScrollElementID.current
      ) as HTMLDivElement;
      if (ele) ele.scrollIntoView();
    }
  }, [selectedChatMessages]);

  // Remember the scroll position before chat message list updating
  function setChatMessageListStoreScrollPos(messages: ChatMessage[]) {
    messageListScrollElementID.current = getScrollAnchorElement();
    console.log(
      `messageListScrollElementID = ${messageListScrollElementID.current}`
    );
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
          <Flex h="calc(100vh - 2rem)" direction="column">
            <Box overflowY="auto" id="chat-messages-scroll-area">
              <MessageListComponent
                messages={selectedChatMessages}
                onMessageEdit={chatClient.current.editMessage.bind(
                  chatClient.current
                )}
                onLoadPrevClick={() =>
                  chatClient.current.loadPreviousMessages(selectedChat.id)
                }
                currentUserID={clientId}
              />
            </Box>
            <Spacer />
            <SendMessageComponent
              onSendMessage={chatClient.current.sendMessage.bind(
                chatClient.current
              )}
              selectedChatID={selectedChat.id}
            />
          </Flex>
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

function getScrollAnchorElement(): string | null {
  const messageListScrollArea = document.querySelector(
    "#chat-messages-scroll-area"
  ) as HTMLDivElement;

  if (!messageListScrollArea) return null;

  const scrollPosBottom =
    messageListScrollArea.scrollHeight -
    messageListScrollArea.clientHeight -
    messageListScrollArea.scrollTop;
  if (messageListScrollArea.scrollTop < 10) {
    const messageListContainer = document.querySelector(
      "#chat-messages-container"
    ) as HTMLDivElement;
    if (messageListContainer)
      return (messageListContainer.childNodes[0] as HTMLBaseElement).id;
    else return null;
  } else if (scrollPosBottom < 10) {
    return "chat-messages-bottom";
  } else {
    return null;
  }
}

export default App;
