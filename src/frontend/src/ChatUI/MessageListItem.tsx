import React, { memo } from "react";
import { ChatMessage } from "../ChatDataTypes";
import {
  Card,
  CardHeader,
  Flex,
  Text,
  CardBody,
  Spacer,
  Button,
  Skeleton,
} from "@chakra-ui/react";
import { TiEdit } from "react-icons/ti";

interface MessageListItemComponentParams {
    message: ChatMessage;
    currentUserID: string | null;
    onShowEditMessageWindow: (message: ChatMessage) => void;
}

const MessageListItemComponent = memo(
    function MessageListItemComponent({
      message,
      currentUserID,
      onShowEditMessageWindow,
    }: MessageListItemComponentParams) {
      console.log(`repainting message ${message.id}`);
      return (
        <Card w="md" id={"chat-message-" + message.id}>
          {!message.is_notification && (
            <CardHeader
              textColor="lightgray"
              fontWeight="bold"
              p="2"
              paddingBottom="0"
            >
              <Flex direction="row">
                <Skeleton height="20px" isLoaded={message.senderName != undefined}>
                  <Text>{message.senderName || "Loading.."}</Text>
                </Skeleton>
                <Spacer />
                {currentUserID === message.sender_id && (
                  <Button
                    rightIcon={<TiEdit />}
                    variant="link"
                    onClick={() =>
                      onShowEditMessageWindow(message)
                    }
                  />
                )}
              </Flex>
            </CardHeader>
          )}
          <CardBody>
            <Text whiteSpace='pre-line'>
              {message.text}
            </Text>
          </CardBody>
        </Card>
      );
    }
);


export { MessageListItemComponent };
