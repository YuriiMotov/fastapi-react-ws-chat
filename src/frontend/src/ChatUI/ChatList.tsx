import { useState} from 'react'
import React from 'react';
import { ChatDataExtended } from '../ChatClient';
import { Card, CardHeader, CardBody, CardFooter, Avatar, Box, Heading, Flex, Text, Button, VStack } from '@chakra-ui/react';


interface ChatListLineComponentParams {
    chat: ChatDataExtended;
    selected: boolean;
    onClick: React.MouseEventHandler<HTMLButtonElement>;
}

function ChatListLineComponent(params: ChatListLineComponentParams) {
    return (
        <Button width='100%' colorScheme='telegram' variant={params.selected ? 'solid' : 'outline'} onClick={params.onClick}>
            <Flex flex='1' gap='4' alignItems='center' flexWrap='wrap'>
                <Avatar name={params.chat.title} src='/public/defaultavatar.png' size='sm' />
                <Box>
                    <Text fontSize='small'>{params.chat.title}</Text>
                    <Text fontSize='x-small'> 1{params.chat.last_message_text}</Text>
                </Box>
            </Flex>
        </Button>
    )
}


interface ChatListComponentParams {
    chatList: ChatDataExtended[];
    selectedChatId?: string;
    onChatSelect: (chat: ChatDataExtended)=>void;
}

function ChatListComponent(params: ChatListComponentParams) {



    return (
        <VStack spacing="1">
            {
                params.chatList.map((chat)=> (
                    <ChatListLineComponent key={chat.id} chat={chat} selected={params.selectedChatId === chat.id} onClick={()=>params.onChatSelect(chat)}/>
                ))
            }
        </VStack>
    )
}

export {ChatListComponent};
