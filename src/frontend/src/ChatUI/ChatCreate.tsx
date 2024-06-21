import React, { forwardRef, useImperativeHandle, useState } from "react";
import { ChatData } from "../ChatDataTypes";
import { Button, Input, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay, useDisclosure } from "@chakra-ui/react";
import { v4 as uuidv4 } from 'uuid';

interface ChatCreateComponentParams {
  currentUserID: string | null;
  onSubmit: (chat_info: ChatData) => void;
}

interface ChatCreateComponentRef {
  show: () => void;
}

const ChatCreateComponent = forwardRef<ChatCreateComponentRef, ChatCreateComponentParams>((params, ref) => {
  const [ chatTitleINput, setChatTitleInput ] = useState('');
  const { isOpen, onOpen, onClose } = useDisclosure();

  useImperativeHandle(ref, () => {
    return {
      show: onOpen
    };
  }, []);

  function onSubmitClick() {
    const chat_info: ChatData = {
      id: uuidv4(),
      title: chatTitleINput,
      owner_id: params.currentUserID!,
    };
    params.onSubmit(chat_info);
    closeModal();
  }

  function closeModal() {
    setChatTitleInput('');
    onClose();
  }

  return (
    <Modal isOpen={isOpen} onClose={closeModal}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Create new chat</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <Input value={chatTitleINput} onChange={(e)=>setChatTitleInput(e.target.value)} />
        </ModalBody>
        <ModalFooter>
          <Button onClick={onSubmitClick}>Create chat</Button>
          <Button variant="ghost" onClick={closeModal}>
            Cancel
          </Button>
          </ModalFooter>
      </ModalContent>
    </Modal>
  );

})



export { ChatCreateComponent, ChatCreateComponentRef };
