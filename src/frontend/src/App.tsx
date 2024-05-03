import React from 'react';
import { useState, useEffect, useRef } from 'react'
import { ChatClient, ChatDataExtended, ChatMessage } from './ChatClient';
import { ChatListComponent } from './ChatUI/ChatList';
import { Box, Button, Flex, HStack, Input, VStack, Text, Spacer, Grid, GridItem } from '@chakra-ui/react';

function App() {

  const [clientId, setClientId] = useState("ef376e46-db3b-4beb-8170-82940d849847");
  const [reconnectCount, setReconnectCount] = useState(0);
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
      [clientId, reconnectCount, ]
  );


  return (
        <Grid h='calc(100vh)' templateRows='1fc' templateColumns='200px 1fr 200px' gap='4' >

          <GridItem p='2'>
            <h4>Chat list:</h4>
            <ChatListComponent chatList={chatList} selectedChatId={selectedChat?.id} onChatSelect={chatClient.current.selectChat.bind(chatClient.current)} />

          </GridItem>

          <GridItem p='2'>
            <Flex h='calc(100vh)' border='1px' direction='column'>
              <Box w='100%' h='100%' overflow='scroll'>
                {
                  (selectedChat !== null) ? (
                    <Button colorScheme='telegram' variant='outline' size='sm' onClick={()=>chatClient.current.loadPreviousMessages(selectedChat.id)}>Load prev</Button>
                  ) : null
                }

                {
                  selectedChatMessages.map((message) => (
                    <Text key={message.id}>{message.text} <Button variant='link' onClick={()=>chatClient.current.editMessage(message.id, message.text + " edited")}>Edit</Button> </Text>
                  ))
                }
              </Box>
              <Spacer />
              {
                  (selectedChat !== null) ? (
                    <HStack spacing='1'>
                      <Input colorScheme='telegram' value={sendMessageText} onChange={(e)=>setSendMessageText(e.target.value)} />
                      <Button colorScheme='telegram' onClick={()=>chatClient.current.sendMessage(sendMessageText, selectedChat.id)}>Send</Button>
                    </HStack>
                  ): (<b>Chat not selected</b>)
                }
            </Flex>
          </GridItem>

          <GridItem p='4'>
            <VStack spacing='3'>
              <Button onClick={()=>chatClient.current.addUserToChat(clientId, "eccf5b4a-c706-4c05-9ab2-5edc7539daad")}>
                Add yourself to forth chat
              </Button>
              <Button onClick={()=>setReconnectCount(reconnectCount + 1)}>Reconnect</Button>
            </VStack>

          </GridItem>

          {/* <Box w="sm" h='100%'>
          </Box>
          <Box w='sm'>
          </Box> */}

        </Grid>
  )
}

export default App
