import React from 'react';
import { ChatDataExtended, ChatMessage } from '../ChatClient';
import { Card, CardHeader, Avatar, Box, Heading, Flex, Text,VStack, LinkBox, LinkOverlay, CardBody, Link, Spacer, Button, Modal, ModalOverlay, ModalContent, ModalHeader, ModalCloseButton, ModalBody, Textarea, ModalFooter} from '@chakra-ui/react';
import { TiEdit } from "react-icons/ti";
import { useDisclosure } from '@chakra-ui/react'

interface MessageListItemComponentParams {
    message: ChatMessage;
    onMessageEdit: (messageId: string, newText: string)=>void;
}

function MessageListItemComponent(params: MessageListItemComponentParams) {

    const { isOpen, onOpen, onClose } = useDisclosure();

    function onSave() {
        const ele = document.querySelector("#message-text-" + params.message.id) as HTMLTextAreaElement;
        if (ele) {
            params.onMessageEdit(params.message.id, ele.value);
            onClose();
        }

    }

    return (
        <Card minW='md'>
            <CardHeader textColor='lightgray' fontWeight='bold' p='2' paddingBottom='0'>
                <Flex direction='row'>
                    <Text>John Doe</Text>
                    <Spacer />
                    {/* <Button rightIcon={<TiEdit />} variant='link' onClick={()=>params.onMessageEdit(params.message.id, params.message.text + " edited")}></Button> */}
                    <Button rightIcon={<TiEdit />} variant='link' onClick={onOpen}></Button>
                    <Modal isOpen={isOpen} onClose={onClose}>
                        <ModalOverlay />
                        <ModalContent>
                            <ModalHeader>Message editing</ModalHeader>
                            <ModalCloseButton />
                            <ModalBody>
                                <Textarea id={'message-text-' + params.message.id} defaultValue={params.message.text} isReadOnly={false} />
                            </ModalBody>
                            <ModalFooter>
                                <Button colorScheme='telegram' mr={3} onClick={onSave}>Save</Button>
                                <Button variant='ghost' onClick={onClose}>Cancel</Button>
                            </ModalFooter>
                        </ModalContent>
                    </Modal>
                </Flex>
            </CardHeader>
            <CardBody>
                {params.message.text.split('\n').map((l,index)=>(<Text key={index}>{l}</Text>))}
            </CardBody>
        </Card>
    )
}


interface MessageListComponentParams {
    messages: ChatMessage[];
    onMessageEdit: (messageId: string, newText: string)=>void;
}


function MessageListComponent(params: MessageListComponentParams) {

    return (
        <VStack spacing='1' paddingBottom='4'>
            {
                params.messages.map((message) => (
                    <MessageListItemComponent key={message.id} message={message} onMessageEdit={params.onMessageEdit} />
                ))
            }
            <Link id='chat-messages-bottom'></Link>
        </VStack>
    )
}

export {MessageListComponent};
