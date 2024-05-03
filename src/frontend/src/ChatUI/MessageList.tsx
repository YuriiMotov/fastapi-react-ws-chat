import React from 'react';
import { ChatDataExtended, ChatMessage } from '../ChatClient';
import { Card, CardHeader, Avatar, Box, Heading, Flex, Text,VStack, LinkBox, LinkOverlay, CardBody} from '@chakra-ui/react';


interface MessageListItemComponentParams {
    message: ChatMessage;
}

function MessageListItemComponent(params: MessageListItemComponentParams) {

    return (
        <Card minW='md'>
            <CardHeader textColor='lightgray' fontWeight='bold' p='2' paddingBottom='0'>
                John Doe
            </CardHeader>
            <CardBody>
                {params.message.text}
            </CardBody>
        </Card>
        // <Button variant='link' onClick={()=>chatClient.current.editMessage(message.id, message.text + " edited")}>Edit</Button>
    )
}


interface MessageListComponentParams {
    messages: ChatMessage[];
}


function MessageListComponent(params: MessageListComponentParams) {

    return (
        <VStack spacing='1'>
            {
                params.messages.map((message) => (
                    <MessageListItemComponent key={message.id} message={message} />
                ))
            }
        </VStack>
    )
}

export {MessageListComponent};
