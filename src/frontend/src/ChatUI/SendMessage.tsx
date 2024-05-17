import React, { useState } from "react";
import { Button, Textarea, HStack } from "@chakra-ui/react";

interface SendMessageComponentParams {
  selectedChatID: string;
  onSendMessage: (messageText: string, chatId: string) => void;
}

function SendMessageComponent({
  selectedChatID,
  onSendMessage,
}: SendMessageComponentParams) {
  const [sendMessageText, setSendMessageText] = useState("");

  function sendMessage() {
    onSendMessage(sendMessageText, selectedChatID);
    setSendMessageText("");
  }

  return (
    <HStack spacing="1">
      <Textarea
        colorScheme="telegram"
        value={sendMessageText}
        onChange={(e) => setSendMessageText(e.target.value)}
        placeholder="Input message to send"
        size="sm"
      />
      <Button colorScheme="telegram" onClick={sendMessage}>
        Send
      </Button>
    </HStack>
  );
}

export { SendMessageComponent };
