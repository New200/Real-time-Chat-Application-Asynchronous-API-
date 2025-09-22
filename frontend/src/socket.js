import { io } from "socket.io-client";

export function createSocket(token) {
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
  return io(API_URL, {
    path: "/ws/socket.io",
    auth: { token },
    autoConnect: true,
  });
}
