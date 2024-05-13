import React, { useState } from 'react';
import { ChatMessage } from '../ChatClient';
import {
    Card,
    CardHeader,
    Flex,
    Text,
    VStack,
    CardBody,
    Link,
    Spacer,
    Button,
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalCloseButton,
    ModalBody,
    Textarea,
    ModalFooter,
    Skeleton,
} from '@chakra-ui/react';
import { TiEdit } from "react-icons/ti";
import { useDisclosure } from '@chakra-ui/react'

interface MessageListItemComponentParams {
    message: ChatMessage;
    currentUserID: string | null;
    onShowEditMessageWindow: (messageId: string, text: string)=>void;
}

function MessageListItemComponent(params: MessageListItemComponentParams) {

    // console.log(`repainting message ${params.message.id}`);
    return (
        <Card minW='md' id={'chat-message-' + params.message.id}>
            {(!params.message.is_notification) && (
                <CardHeader textColor='lightgray' fontWeight='bold' p='2' paddingBottom='0'>
                    <Flex direction='row'>
                        <Skeleton height='20px' isLoaded={params.message.senderName != undefined}>
                            <Text>{params.message.senderName || 'Loading..'}</Text>
                        </Skeleton>
                        <Spacer />
                        {(params.currentUserID === params.message.sender_id) && (
                                <Button
                                    rightIcon={<TiEdit />}
                                    variant='link'
                                    onClick={()=>params.onShowEditMessageWindow(params.message.id, params.message.text)}
                                >
                                </Button>
                        )}
                    </Flex>
                </CardHeader>
            )}
            <CardBody>
                {params.message.text.split('\n').map((l,index)=>(<Text key={index}>{l}</Text>))}
            </CardBody>
        </Card>
    )
}


interface MessageListComponentParams {
    messages: ChatMessage[];
    currentUserID: string | null;
    onMessageEdit: (messageId: string, newText: string)=>void;
}


function MessageListComponent(params: MessageListComponentParams) {

    const { isOpen, onOpen, onClose } = useDisclosure();
    const [ editedMessageId, setEditedMessageId ] = useState<string | null>(null);
    const [ editedMessageText, setEditedMessageText ] = useState<string | null>(null);

    function onSave() {
        const ele = document.querySelector("#message-edit-text") as HTMLTextAreaElement;
        if (ele && editedMessageId) {
            params.onMessageEdit(editedMessageId, ele.value);
            onClose();
        } else {
            console.log(`Can't save message. ele is ${ele}, editedMessageId is ${editedMessageId}`);
            onClose();
        }
    }

    function showEditMessageWindow(messageId: string, text: string) {
        setEditedMessageId(messageId);
        setEditedMessageText(text);
        onOpen();
    }

    return (
        <VStack spacing='1' paddingBottom='4' id='chat-messages-container'>
            {
                params.messages.map((message) => (
                    <MessageListItemComponent
                        key={message.id}
                        message={message}
                        onShowEditMessageWindow={showEditMessageWindow}
                        currentUserID={params.currentUserID}
                    />
                ))
            }
            <Modal isOpen={isOpen} onClose={onClose}>
                <ModalOverlay />
                <ModalContent>
                    <ModalHeader>Message editing</ModalHeader>
                    <ModalCloseButton />
                    <ModalBody>
                        <Textarea
                            id='message-edit-text'
                            defaultValue={editedMessageText ? editedMessageText : ''}
                            isReadOnly={false}
                        />
                    </ModalBody>
                    <ModalFooter>
                        <Button colorScheme='telegram' mr={3} onClick={onSave}>Save</Button>
                        <Button variant='ghost' onClick={onClose}>Cancel</Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>

            <Link id='chat-messages-bottom'></Link>
        </VStack>
    )
}

export {MessageListComponent};
