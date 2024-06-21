interface ChatData {
  id: string;
  title: string;
  owner_id: string;
}

interface ChatDataExtended extends ChatData {
  last_message_text: string | null;
  members_count: number;
}

interface ChatMessage {
  id: string;
  chat_id: string;
  dt: string;
  text: string;
  is_notification: string;
  sender_id?: string;
  params?: string;
  senderName?: string;
}

interface User {
  id: string;
  name: string;
}


export { ChatData, ChatDataExtended, ChatMessage, User };
