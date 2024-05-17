import React from "react";
import { ChatDataExtended } from "../ChatDataTypes";
import {
  VStack,
  Button,
  Select,
} from "@chakra-ui/react";

interface ServiceButtonsBlockCompnentParams {
    clientID: string;
    chatList: ChatDataExtended[];
    onSetClientID: (clientID: string) => void;
    onAddUserToChat: (userID: string, chatID: string) => void;
    onIncReconnectCount: () => void;
}

function ServiceButtonsBlockCompnent({
    clientID,
    chatList,
    onSetClientID,
    onAddUserToChat,
    onIncReconnectCount,
}: ServiceButtonsBlockCompnentParams) {

    return (
        <VStack spacing="3">
          <Select
            placeholder="Select option"
            onChange={(e) => onSetClientID(e.target.value)}
          >
            <option value="-">-</option>
            <option value="ef376e46-db3b-4beb-8170-82940d849847">John</option>
            <option value="ef376e56-db3b-4beb-8170-82940d849847">Joe</option>
          </Select>
          {clientID === "ef376e46-db3b-4beb-8170-82940d849847" &&
            chatList.length < 4 && (
              <Button
                onClick={() =>
                  onAddUserToChat(clientID, "eccf5b4a-c706-4c05-9ab2-5edc7539daad")
                }
              >
                Add yourself to forth chat
              </Button>
            )}
          {clientID === "ef376e46-db3b-4beb-8170-82940d849847" && (
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
