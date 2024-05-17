import React, { useEffect, useState } from "react";
import { ChatMessage } from "../ChatDataTypes";
import {
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  Textarea,
  ModalFooter,
} from "@chakra-ui/react";
import { useDisclosure } from "@chakra-ui/react";


interface MessageEditWindowComponentParams {
  editedMessage: ChatMessage | null;
  onMessageEditSave: (messageID: string, newText: string) => void;
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


export { MessageEditWindowComponent };
