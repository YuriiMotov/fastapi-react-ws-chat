import React, { useEffect, useState, useCallback, useRef } from "react";
import { ChatMessage } from "../ChatClient";
import { VStack, Link, Button } from "@chakra-ui/react";
import { MessageListItemComponent } from "./MessageListItem";
import { MessageEditWindowComponent } from "./MessageEditWindow";


interface MessageListComponentParams {
  messages: ChatMessage[];
  currentUserID: string | null;
  chatID: string;
  messageListScrollElementID: React.MutableRefObject<string | null>;
  onEditMessage: (messageId: string, newText: string) => void;
  onLoadPrevClick: () => void;
}

function MessageListComponent({
  messages,
  currentUserID,
  chatID,
  messageListScrollElementID,
  onEditMessage: onMessageEdit,
  onLoadPrevClick,
}: MessageListComponentParams) {
  const [editedMessage, setEditedMessage] = useState<ChatMessage | null>(null);
  const prevChatID = useRef(chatID);


  const showEditMessageWindow = useCallback((message: ChatMessage) => {
      setEditedMessage(message);
    }, []
  );

  function resetEditedMessage() {
    setEditedMessage(null);
  }


  // Scroll message list container on message list update
  useEffect(() => {

    if (chatID !== prevChatID.current) {
      console.log('ChatID changed! Scroll to the bottom!');
      messageListScrollElementID.current = "chat-messages-bottom";
      prevChatID.current = chatID;
    }

    if (messageListScrollElementID.current) {
      console.log(`messages updated. messageListScrollElementID is ${messageListScrollElementID.current} `);

      const ele = document.querySelector(
        "#" + messageListScrollElementID.current
      ) as HTMLDivElement;

      if (ele) ele.scrollIntoView();
    }

  }, [messages, chatID]);

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
