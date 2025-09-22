import React, { useState, useEffect } from "react";
import { createSocket } from "./socket";

function App() {
  const [token, setToken] = useState("");
  const [socket, setSocket] = useState(null);
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");

  useEffect(() => {
    if (!socket) return;
    socket.on("new_message", (msg) => setMessages((m) => [msg, ...m]));
    return () => {
      socket.off("new_message");
    };
  }, [socket]);

  async function login() {
    const form = new URLSearchParams();
    form.append("username", "alice");
    form.append("password", "wonder");
    const res = await fetch(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/token`, {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    setToken(data.access_token);
    const s = createSocket(data.access_token);
    setSocket(s);
  }

  function send() {
    if (socket) {
      socket.emit("send_message", { room: "global", text });
      setText("");
    }
  }

  return (
    <div>
      <h1>Chat</h1>
      {!token && <button onClick={login}>Login</button>}
      <div>
        <input value={text} onChange={(e) => setText(e.target.value)} />
        <button onClick={send}>Send</button>
      </div>
      <ul>
        {messages.map((m, i) => (
          <li key={i}>{m.user}: {m.text}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;
