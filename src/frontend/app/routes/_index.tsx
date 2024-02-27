import type { MetaFunction } from "@remix-run/node";

export const meta: MetaFunction = () => {
  return [
    { title: "FastAPI-React websocket app" },
    { name: "Chat app on FastAPI and React", content: "Welcome to FastAPI-React websocket app" },
  ];
};

export default function Index() {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", lineHeight: "1.8" }}>
      <h1>Welcome chat</h1>
      <div>
        <div>
          <span>List of chats:</span>
        </div>
        <div>
          <span>Chat content</span>
        </div>
      </div>

    </div>
  );
}
