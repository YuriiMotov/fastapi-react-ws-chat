import React, { forwardRef, useImperativeHandle, useRef } from "react";
import { Box, Flex, Spacer } from "@chakra-ui/react";
import { MessageListComponent, getScrollAnchorElement } from "./MessageList";
import { SendMessageComponent } from "./SendMessage";
import { ChatDataExtended, ChatMessage } from "../ChatClient";


interface ChatParams {
    h: string;
    currentUserID: string;
    chat: ChatDataExtended;
    chatMessages: ChatMessage[];
    onSendMessage: (messageText: string, chatID: string) => void;
    onEditMessage: (messageID: string, newText: string) => void;
    onLoadPrevMessagesClick: (chatID: string) => void;
}


interface ChatComponentRef {
    onBeforMessageListChangeCallback: () => void;
}


const ChatComponent = forwardRef<ChatComponentRef, ChatParams>((params, ref) => {

    const messageListScrollElementID = useRef<string | null>(
        "chat-messages-bottom"
      );

    useImperativeHandle(ref, () => {
        return {
          onBeforMessageListChangeCallback() {
            console.log('onBeforMessageListChangeCallback is called');
            messageListScrollElementID.current = getScrollAnchorElement();
          },
        };
      }, []);

    return (
      <Flex h={params.h} direction="column">
        <Box overflowY="auto" id="chat-messages-scroll-area">
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
