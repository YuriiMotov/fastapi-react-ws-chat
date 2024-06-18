import React from "react";
import { ChatDataExtended } from "../ChatDataTypes";
import {
  VStack,
  Button,
} from "@chakra-ui/react";

interface ServiceButtonsBlockCompnentParams {
    clientID: string;
    chatList: ChatDataExtended[];
    onAddUserToChat: (userID: string, chatID: string) => void;
    onIncReconnectCount: () => void;
}

function ServiceButtonsBlockCompnent({
    clientID,
    chatList,
    onAddUserToChat,
    onIncReconnectCount,
}: ServiceButtonsBlockCompnentParams) {

    return (
        <VStack spacing="3">
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
