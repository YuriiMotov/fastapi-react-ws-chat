import React from 'react';
import { ChatDataExtended } from '../ChatClient';
import { Card, CardHeader, Avatar, Box, Heading, Flex, Text,VStack, LinkBox, LinkOverlay} from '@chakra-ui/react';

const maxChatItemTextLength = 25;

function limitText(text: string, limit: number) {
    return text.length < limit ? text : (text.slice(0, limit) + '..')
}

interface ChatListLineComponentParams {
    chat: ChatDataExtended;
    selected: boolean;
    onClick: React.MouseEventHandler<HTMLAnchorElement>;
}

function ChatListLineComponent(params: ChatListLineComponentParams) {
    return (
        <LinkBox as='button' w='100%' maxH='sm' >
            <Card variant={params.selected ? 'filled' : 'elevated'} size='sm' w='100%'>
                <CardHeader>
                    <Flex flex='1' gap='4' alignItems='left' flexWrap='wrap'>
                        <Avatar name={params.chat.title} src='/public/defaultavatar.png' size='sm' />
                        <Box textAlign='left'>
                            <LinkOverlay href='#' onClick={params.onClick} >
                                {params.chat.title}
                            </LinkOverlay>
                            {
                            params.chat.last_message_text ? (
                                <Text fontSize='x-small' textColor='gray'>{limitText(params.chat.last_message_text, maxChatItemTextLength)}</Text>
                            ) : null
                            }
                        </Box>
                    </Flex>
                </CardHeader>
            </Card>
        </LinkBox>
    )
}


interface ChatListComponentParams {
    chatList: ChatDataExtended[];
    selectedChatId?: string;
    onChatSelect: (chat: ChatDataExtended)=>void;
}

function ChatListComponent(params: ChatListComponentParams) {
    return (
        <VStack spacing="1" w='100%'>
            <Heading size='sm'>Chat list:</Heading>
            {
                params.chatList.map((chat)=> (
                    <ChatListLineComponent key={chat.id} chat={chat} selected={params.selectedChatId === chat.id} onClick={()=>params.onChatSelect(chat)}/>
                ))
            }
        </VStack>
    )
}

export {ChatListComponent};
