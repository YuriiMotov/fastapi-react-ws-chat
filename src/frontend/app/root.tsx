import { json } from "@remix-run/node";
import type { LinksFunction } from "@remix-run/node";
import {
  Form,
  Link,
  Links,
  LiveReload,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  useLoaderData,
} from "@remix-run/react";

import { getChats } from "./data";
import defaultAvatar from "./images/default-avatar.png"


export const loader = async () => {
  const chats = await getChats();
  return json({ chats: chats });
};

export default function App() {
  const { chats } = useLoaderData<typeof loader>();
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1"
        />
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossOrigin="anonymous" />

        <Meta />
        <Links />
      </head>
      <body>

    <section style={{backgroundColor: "#eee"}}>
        <div className="container py-5">
            <div className="row">
                <div className="col-md-6 col-lg-5 col-xl-4 mb-4 mb-md-0">
                    <h5 className="font-weight-bold mb-3 text-center text-lg-start">Chats</h5>

                    {chats.length ? (
                        <div className="card">
                            <div className="card-body">
                                <ul className="list-unstyled mb-0">
                                {chats.map((chat) => (
                                    <li key={chat.id} className="p-2 border-bottom" style={{backgroundColor: "#eee"}}>
                                        <Link className="d-flex justify-content-between" to={`chats/${chat.id}`}>
                                            <div className="d-flex flex-row">
                                                <img src={defaultAvatar} alt="avatar" className="rounded-circle d-flex align-self-center me-3 shadow-1-strong" width="60" />
                                                <div className="pt-1">
                                                    <p className="fw-bold mb-0">{chat.title}</p>
                                                    <p className="small text-muted">{chat.last_message_text}</p>
                                                </div>
                                            </div>
                                        </Link>
                                    </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    ) : (
                        <p>
                            <i>No chats</i>
                        </p>
                    )}

                </div>

                <Outlet />

            </div>
        </div>
    </section>

    </body>
    </html>

        );
}
