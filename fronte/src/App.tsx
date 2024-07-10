import React, { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [message, setMessage] = useState<string>("");
  const [socket, setSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:7000/ws`);

    ws.onopen = function () {
      console.log("WebSocket connection established");
      ws.send("hello from react");
    };

    ws.onmessage = function (event: MessageEvent) {
      console.log("message from server:", event.data);
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, []);

  const send = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(message);
      setMessage("");
    } else {
      console.error("WebSocket is not connected");
    }
  };

  return (
    <div>
      <input
        type="text"
        value={message}
        onChange={(event: React.ChangeEvent<HTMLInputElement>) => setMessage(event.target.value)}
      />
      <button onClick={send}>Send</button>
    </div>
  );
}

export default App;