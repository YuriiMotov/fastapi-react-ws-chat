import React, { forwardRef, useImperativeHandle, useRef } from "react";
import { Box, Flex, IconButton, Spacer } from "@chakra-ui/react";
import { MessageListComponent, getScrollAnchorElement } from "./MessageList";
import { SendMessageComponent } from "./SendMessage";
import { ChatDataExtended, ChatMessage, User } from "../ChatDataTypes";
import { AddUserToChatComponent, AddUserToChatComponentRef } from "./AddUserToChat";
import { GoPersonAdd } from "react-icons/go";

interface ChatParams {
    h: string;
    currentUserID: string;
    chat: ChatDataExtended;
    chatMessages: ChatMessage[];
    onSendMessage: (messageText: string, chatID: string) => void;
    onEditMessage: (messageID: string, newText: string) => void;
    onLoadPrevMessagesClick: (chatID: string) => void;
    onUserAutocompleteRequest: (inputText: string) => void;
    onAddUserToChatRequest: (userID: string, chatID: string) => void;
}


interface ChatComponentRef {
    onBeforMessageListChangeCallback: () => void;
    onSetUserAutocomplete: (users: User[]) => void;
}


const ChatComponent = forwardRef<ChatComponentRef, ChatParams>((params, ref) => {
    const messageListScrollElementID = useRef<string | null>(
        "chat-messages-bottom"
      );
    const addUserToChatComponentRef = useRef<AddUserToChatComponentRef>(null);

    useImperativeHandle(ref, () => {
        return {
          onBeforMessageListChangeCallback() {
            console.log('onBeforMessageListChangeCallback is called');
            messageListScrollElementID.current = getScrollAnchorElement();
          },
          onSetUserAutocomplete: addUserToChatComponentRef.current!.setAutocomplete,
        };
      }, []);

    function showAddUserToChatWindow() {
      if (addUserToChatComponentRef.current)
        addUserToChatComponentRef.current.show();
    }

    return (
      <Flex h={params.h} direction="column">
        <Box overflowY="auto" id="chat-messages-scroll-area">
          <IconButton aria-label='Add user to chat' icon={<GoPersonAdd />} onClick={showAddUserToChatWindow} />
          <AddUserToChatComponent
            currentUserID={params.currentUserID}
            chat={params.chat}
            onAutocompleteRequest={params.onUserAutocompleteRequest}
            onSubmit={params.onAddUserToChatRequest}
            ref={addUserToChatComponentRef}
          />
          <MessageListComponent
            messages={params.chatMessages}
            chatID={params.chat.id}
            messageListScrollElementID={messageListScrollElementID}
            onEditMessage={params.onEditMessage}
            onLoadPrevClick={()=>params.onLoadPrevMessagesClick(params.chat.id)}
            currentUserID={params.currentUserID}
          />
        </Box>
        <Spacer />
        <SendMessageComponent
          onSendMessage={params.onSendMessage}
          selectedChatID={params.chat.id}
        />
      </Flex>
    )

});


export { ChatComponent, ChatComponentRef };
