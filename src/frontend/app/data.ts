////////////////////////////////////////////////////////////////////////////////
// 🛑 Nothing in here has anything to do with Remix, it's just a fake database
////////////////////////////////////////////////////////////////////////////////

import { matchSorter } from "match-sorter";
// @ts-expect-error - no types, but it's a tiny function
import sortBy from "sort-by";
import invariant from "tiny-invariant";

type ChatMutation = {
  id?: string;
  title?: string;
};

export type ChatRecord = {
  id: string;
  title: string;
  last_message_text: string;
};

////////////////////////////////////////////////////////////////////////////////
// This is just a fake DB table. In a real app you'd be talking to a real db or
// fetching from an existing API.
const fakeChats = {
  records: {} as Record<string, ChatRecord>,

  async getAll(): Promise<ChatRecord[]> {
    return Object.keys(fakeChats.records)
      .map((key) => fakeChats.records[key])
      .sort(sortBy("-createdAt", "last"));
  },

  async get(id: string): Promise<ChatRecord | null> {
    return fakeChats.records[id] || null;
  },

  async create(values: ChatRecord): Promise<ChatRecord> {
    const id = values.id;
    const newChat = { ...values };
    fakeChats.records[id] = newChat;
    return newChat;
  },

  async set(id: string, values: ChatMutation): Promise<ChatRecord> {
    const contact = await fakeChats.get(id);
    invariant(contact, `No contact found for ${id}`);
    const updatedContact = { ...contact, ...values };
    fakeChats.records[id] = updatedContact;
    return updatedContact;
  },

  destroy(id: string): null {
    delete fakeChats.records[id];
    return null;
  },
};

////////////////////////////////////////////////////////////////////////////////
// Handful of helper functions to be called from route loaders and actions
export async function getChats(query?: string | null) {
  await new Promise((resolve) => setTimeout(resolve, 500));
  let chats = await fakeChats.getAll();
  if (query) {
    chats = matchSorter(chats, query, {
      keys: ["first", "last"],
    });
  }
  return chats.sort(sortBy("last", "createdAt"));
}

export async function getChat(id: string) {
  return fakeChats.get(id);
}


[
  {
    id: "123",
    title: "Wife",
    last_message_text: "Hello, Are you there?",
  },
  {
    id: "453",
    title: "Boss",
    last_message_text: "Just do it!",
  },
].forEach((chat) => {
  fakeChats.create({
    ...chat,
  });
});
