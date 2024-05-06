import React from 'react';
import { useState, useEffect, useRef } from 'react'
import { ChatClient, ChatDataExtended, ChatMessage } from './ChatClient';
import { ChatListComponent } from './ChatUI/ChatList';

import { Box, Button, Flex, HStack, Input, VStack, Text, Spacer, Grid, GridItem, Container, Textarea } from '@chakra-ui/react';
import { MessageListComponent } from './ChatUI/MessageList';

function App() {

  const [clientId, setClientId] = useState("ef376e46-db3b-4beb-8170-82940d849847");
  const [reconnectCount, setReconnectCount] = useState(0);
  const [chatList, setChatList] = useState<ChatDataExtended[]>([]);
  const [selectedChat, setSelectedChat] = useState<ChatDataExtended | null>(null);
  const [selectedChatMessages, setSelectedChatMessages] = useState<ChatMessage[]>([]);
  const [sendMessageText, setSendMessageText] = useState("");

  const chatClient = useRef<ChatClient>(new ChatClient(setChatList, setSelectedChat, setChatMessageListStoreScrollPos));
  const connectDelay = useRef<number | null>(null);
  const messageListScrollElementID = useRef<string | null>("chat-messages-bottom");

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
      [clientId, reconnectCount, ]
  );

  useEffect(
    () => {
      if (messageListScrollElementID.current) {
        const ele = document.querySelector('#' + messageListScrollElementID.current) as HTMLDivElement;
        ele.scrollIntoView();
      }
    }, [selectedChatMessages, ]
  );

  function setChatMessageListStoreScrollPos(messages: ChatMessage[]) {
    const messageListScrollArea = document.querySelector("#chat-messages-scroll-area") as HTMLDivElement;
    const messageListScrollAreaTopY = messageListScrollArea.scrollTop;

    if (messageListScrollArea.scrollTop < 10) {
      const messageListContainer = document.querySelector("#chat-messages-container") as HTMLDivElement;
      messageListScrollElementID.current = (messageListContainer.childNodes[0] as HTMLBaseElement).id;
    } else if (((messageListScrollArea.scrollHeight - messageListScrollArea.clientHeight) - messageListScrollAreaTopY) < 10) {
      messageListScrollElementID.current = "chat-messages-bottom";
    } else {
      messageListScrollElementID.current = null;
    }
    console.log(`messageListScrollElementID = ${messageListScrollElementID.current}`);

    setSelectedChatMessages(messages);

  }

  function sendMessageClickHandler() {
    chatClient.current.sendMessage(sendMessageText, selectedChat!.id);
    setSendMessageText("");
  }

  return (
        <Grid h='calc(100vh)' templateRows='1fc' templateColumns='250px 1fr 250px' backgroundColor='whitesmoke' >
          <GridItem>
            <Container p='4'>
              <ChatListComponent chatList={chatList} selectedChatId={selectedChat?.id} onChatSelect={chatClient.current.selectChat.bind(chatClient.current)} />
            </Container>
          </GridItem>

          <GridItem>
            <Flex h='calc(100vh)' direction='column' p='4' backgroundColor='AppWorkspace'>
              <Box w='100%' h='100%' overflow='scroll' id='chat-messages-scroll-area'>
                <VStack spacing='4'>
                  {
                    (selectedChat !== null) ? (
                      <Container minW='unset' centerContent>
                        <Button colorScheme='telegram' variant='link' size='sm' onClick={()=>chatClient.current.loadPreviousMessages(selectedChat.id)}>⇧ Load prev ⇧</Button>
                      </Container>
                    ) : null
                  }
                  <MessageListComponent messages={selectedChatMessages} onMessageEdit={chatClient.current.editMessage.bind(chatClient.current)} />
                </VStack>
              </Box>
              <Spacer />
              {
                  (selectedChat !== null) ? (
                    <HStack spacing='1'>
                      <Textarea
                        colorScheme='telegram'
                        value={sendMessageText}
                        onChange={(e)=>setSendMessageText(e.target.value)}
                        placeholder='Input message to send'
                        size='sm'
                      />
                      <Button colorScheme='telegram' onClick={sendMessageClickHandler}>Send</Button>
                    </HStack>
                  ): (<b>Chat not selected</b>)
                }
            </Flex>
          </GridItem>

          <GridItem>
            <VStack spacing='3' p='4'>
              <Button onClick={()=>chatClient.current.addUserToChat(clientId, "eccf5b4a-c706-4c05-9ab2-5edc7539daad")}>
                Add yourself to forth chat
              </Button>
              <Button onClick={()=>setReconnectCount(reconnectCount + 1)}>Reconnect</Button>
            </VStack>
          </GridItem>

        </Grid>
  )
}

export default App
