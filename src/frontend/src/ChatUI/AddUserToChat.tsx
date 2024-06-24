import React, { forwardRef, useImperativeHandle, useState } from "react";
import { ChatData, User } from "../ChatDataTypes";
import { Text, Button, Card, CardHeader, HStack, Input, LinkBox, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay, Popover, PopoverAnchor, PopoverBody, PopoverContent, PopoverTrigger, useDisclosure, Spinner } from "@chakra-ui/react";

interface UserListLineComponentParams {
  user: User;
  onSelect: (id: string)=>void;
}

function UserListLineComponent(params: UserListLineComponentParams) {

  return (
    <LinkBox as="button" w="100%" onClick={()=>params.onSelect(params.user.id)}>
      <Card variant="elevated" size="sm">
        <CardHeader>
          <Text noOfLines={1} textAlign="left">{params.user.name}</Text>
        </CardHeader>
      </Card>
    </LinkBox>
  );
}


interface AddUserToChatComponentParams {
  currentUserID: string | null;
  chat: ChatData;

  onSubmit: ( userID: string, chatID: string ) => void;
  onAutocompleteRequest: ( inputText: string ) => void;
}

interface AddUserToChatComponentRef {
  show: () => void;
  setAutocomplete: (users: User[]) => void;
}

const AddUserToChatComponent = forwardRef<AddUserToChatComponentRef, AddUserToChatComponentParams>((params, ref) => {
  const [ userNameInput, setUserNameInput ] = useState('');
  const [ autocompleteValues, setAutocompleteValues ] = useState<User[] | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  useImperativeHandle(ref, () => {
    return {
      show: onOpen,
      setAutocomplete: setAutocompleteValues,
    };
  }, []);

  function onSubmitClick(userID: string) {
    params.onSubmit(userID, params.chat.id);
    closeModal();
  }

  function closeModal() {
    setUserNameInput('');
    onClose();
  }

  function onUserNameInput(e) {
    setUserNameInput(e.target.value)
  }

  function onSearchClick() {
    setAutocompleteValues(null);
    params.onAutocompleteRequest(userNameInput);
  }

  return (
    <Modal isOpen={isOpen} onClose={closeModal}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Add user to chat: {params.chat.title}</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <Popover
            onOpen={onSearchClick}
            onClose={()=>setAutocompleteValues(null)}
            closeOnBlur={true}
            isLazy
            lazyBehavior='keepMounted'
          >
            <HStack>
              <PopoverAnchor>
                <Input value={userNameInput} onChange={onUserNameInput} />
              </PopoverAnchor>
              <PopoverTrigger  >
                <Button>
                  Search
                </Button>
              </PopoverTrigger>
            </HStack>
            <PopoverContent>
              <PopoverBody>
                Users:
                  {
                    (autocompleteValues === null) ? (
                      <Spinner />
                    ) : (
                      autocompleteValues.map((user) => (
                        <UserListLineComponent key={user.id} user={user} onSelect={onSubmitClick} />
                      ))
                    )
                  }
              </PopoverBody>
            </PopoverContent>
          </Popover>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" onClick={closeModal}>
            Cancel
          </Button>
          </ModalFooter>
      </ModalContent>
    </Modal>
  );

})


export { AddUserToChatComponent, AddUserToChatComponentRef };
