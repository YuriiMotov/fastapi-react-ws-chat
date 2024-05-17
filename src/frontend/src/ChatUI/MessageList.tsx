import React, { useEffect, useState, useCallback, memo } from "react";
import { ChatMessage } from "../ChatClient";
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
} from "@chakra-ui/react";
import { TiEdit } from "react-icons/ti";
import { useDisclosure } from "@chakra-ui/react";

interface MessageListItemComponentParams {
  message: ChatMessage;
  currentUserID: string | null;
  onShowEditMessageWindow: (message: ChatMessage) => void;
}

const MessageListItemComponent = memo(
  function MessageListItemComponent({
    message,
    currentUserID,
    onShowEditMessageWindow,
  }: MessageListItemComponentParams) {
    console.log(`repainting message ${message.id}`);
    return (
      <Card w="md" id={"chat-message-" + message.id}>
        {!message.is_notification && (
          <CardHeader
            textColor="lightgray"
            fontWeight="bold"
            p="2"
            paddingBottom="0"
          >
            <Flex direction="row">
              <Skeleton height="20px" isLoaded={message.senderName != undefined}>
                <Text>{message.senderName || "Loading.."}</Text>
              </Skeleton>
              <Spacer />
              {currentUserID === message.sender_id && (
                <Button
                  rightIcon={<TiEdit />}
                  variant="link"
                  onClick={() =>
                    onShowEditMessageWindow(message)
                  }
                />
              )}
            </Flex>
          </CardHeader>
        )}
        <CardBody>
          <Text whiteSpace='pre-line'>
            {message.text}
          </Text>
        </CardBody>
      </Card>
    );
  }
);

interface MessageEditWindowComponentParams {
  editedMessage: ChatMessage | null;
  onMessageEditSave: (messageId: string, newText: string) => void;
  resetEditedMessageHandler: () => void;
}

function MessageEditWindowComponent({
  editedMessage,
  onMessageEditSave,
  resetEditedMessageHandler,
}: MessageEditWindowComponentParams) {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [editedMessageText, setEditedMessageText] = useState<string>("");

  useEffect(() => {
    if (editedMessage) {
        setEditedMessageText(editedMessage.text);
        onOpen();
    }
    return () => {
        setEditedMessageText("");
        onClose();
    }
  }, [editedMessage]);

  function closeModal() {
    resetEditedMessageHandler();
    onClose();
  }

  function saveAndClose() {
    onMessageEditSave(editedMessage!.id, editedMessageText);
    closeModal();
  }

  return (
    <Modal isOpen={isOpen} onClose={closeModal}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Message editing</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <Textarea
            id="message-edit-text"
            value={editedMessageText}
            onChange={(e)=>setEditedMessageText(e.target.value)}
            isReadOnly={false}
          />
        </ModalBody>
        <ModalFooter>
          <Button
            colorScheme="telegram"
            mr={3}
            onClick={saveAndClose}
          >
            Save
          </Button>
          <Button variant="ghost" onClick={closeModal}>
            Cancel
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

interface MessageListComponentParams {
  messages: ChatMessage[];
  currentUserID: string | null;
  messageListScrollElementID: React.MutableRefObject<string | null>;
  onEditMessage: (messageId: string, newText: string) => void;
  onLoadPrevClick: () => void;
}

function MessageListComponent({
  messages,
  currentUserID,
  messageListScrollElementID,
  onEditMessage: onMessageEdit,
  onLoadPrevClick,
}: MessageListComponentParams) {
  const [editedMessage, setEditedMessage] = useState<ChatMessage | null>(null);

  const showEditMessageWindow = useCallback((message: ChatMessage) => {
      setEditedMessage(message);
    }, []
  );

  function resetEditedMessage() {
    setEditedMessage(null);
  }


  // Scroll message list container on message list update
  useEffect(() => {
    console.log(`messages updated. messageListScrollElementID is ${messageListScrollElementID.current} `);
    if (messageListScrollElementID.current) {
      const ele = document.querySelector(
        "#" + messageListScrollElementID.current
      ) as HTMLDivElement;

      if (ele) ele.scrollIntoView();
    }
  }, [messages]);

  return (
    <VStack spacing="4" paddingBottom="4" id="chat-messages-container">
      <Button
        colorScheme="telegram"
        variant="link"
        size="sm"
        onClick={onLoadPrevClick}
      >
        ⇧ Load prev ⇧
      </Button>
      {messages.map((message) => (
        <MessageListItemComponent
          key={message.id}
          message={message}
          onShowEditMessageWindow={showEditMessageWindow}
          currentUserID={currentUserID}
        />
      ))}
      <Link id="chat-messages-bottom"></Link>
      <MessageEditWindowComponent
        editedMessage={editedMessage}
        onMessageEditSave={onMessageEdit}
        resetEditedMessageHandler={resetEditedMessage}
      />
    </VStack>
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

    if (messageListContainer) {
      const aID = (messageListContainer.childNodes[1] as HTMLBaseElement).id;
      return aID;
    } else {
      console.log('messageListContainer not found');
      return null
    };

  } else if (scrollPosBottom < 10) {
    return "chat-messages-bottom";
  } else {
    return null;
  }
}


export { MessageListComponent, getScrollAnchorElement };
