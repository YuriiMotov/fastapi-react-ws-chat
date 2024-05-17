import React from "react";
import { ChatDataExtended } from "../ChatClient";
import {
  VStack,
  Button,
  Select,
} from "@chakra-ui/react";

interface ServiceButtonsBlockCompnentParams {
    clientId: string;
    chatList: ChatDataExtended[];
    onSetClientId: (clientID: string) => void;
    onAddUserToChat: (userID: string, chatID: string) => void;
    onIncReconnectCount: () => void;
}

function ServiceButtonsBlockCompnent({
    clientId,
    chatList,
    onSetClientId,
    onAddUserToChat,
    onIncReconnectCount,
}: ServiceButtonsBlockCompnentParams) {

    return (
        <VStack spacing="3">
          <Select
            placeholder="Select option"
            onChange={(e) => onSetClientId(e.target.value)}
          >
            <option value="-">-</option>
            <option value="ef376e46-db3b-4beb-8170-82940d849847">John</option>
            <option value="ef376e56-db3b-4beb-8170-82940d849847">Joe</option>
          </Select>
          {clientId === "ef376e46-db3b-4beb-8170-82940d849847" &&
            chatList.length < 4 && (
              <Button
                onClick={() =>
                  onAddUserToChat(clientId, "eccf5b4a-c706-4c05-9ab2-5edc7539daad")
                }
              >
                Add yourself to forth chat
              </Button>
            )}
          {clientId === "ef376e46-db3b-4beb-8170-82940d849847" && (
            <Button
              onClick={() =>
                onAddUserToChat(
                    "ef376e56-db3b-4beb-8170-82940d849847",
                    "eccf5b4a-c706-4c05-9ab2-5edc7539daad"
                )
              }
            >
              Add Joe to forth chat
            </Button>
          )}
          <Button onClick={onIncReconnectCount}>
            Reconnect
          </Button>
        </VStack>
    )
};

export {ServiceButtonsBlockCompnent};
