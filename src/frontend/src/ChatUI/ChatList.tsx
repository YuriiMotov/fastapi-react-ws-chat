import React from "react";
import { ChatDataExtended } from "../ChatClient";
import {
  Card,
  CardHeader,
  Avatar,
  Box,
  Heading,
  Flex,
  Text,
  VStack,
  LinkBox,
} from "@chakra-ui/react";

interface ChatListLineComponentParams {
  chat: ChatDataExtended;
  selected: boolean;
  onClick: React.MouseEventHandler<HTMLDivElement>;
}

function ChatListLineComponent({
  chat,
  selected,
  onClick,
}: ChatListLineComponentParams) {
  return (
    <LinkBox as="button" w="100%" onClick={onClick}>
      <Card variant={selected ? "filled" : "elevated"} size="sm">
        <CardHeader>
          <Flex gap="4">
            <Avatar
              name={chat.title}
              src="/public/defaultavatar.png"
              size="sm"
            />
            <Box textAlign="left">
              <Text noOfLines={1}>{chat.title}</Text>
              <Text fontSize="x-small" textColor="gray" noOfLines={1}>
                {chat.last_message_text}
              </Text>
            </Box>
          </Flex>
        </CardHeader>
      </Card>
    </LinkBox>
  );
}

interface ChatListComponentParams {
  chatList: ChatDataExtended[];
  selectedChatID?: string;
  onChatSelect: (chat: ChatDataExtended) => void;
}

function ChatListComponent({
  chatList,
  selectedChatID,
  onChatSelect,
}: ChatListComponentParams) {
  return (
    <VStack spacing="1" w="100%">
      <Heading size="sm">Chat list:</Heading>
      {chatList.map((chat) => (
        <ChatListLineComponent
          key={chat.id}
          chat={chat}
          selected={selectedChatID === chat.id}
          onClick={() => onChatSelect(chat)}
        />
      ))}
    </VStack>
  );
}

export { ChatListComponent };
