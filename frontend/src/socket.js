import { io } from "socket.io-client";

export function createSocket(token) {
  // adjust API_URL to your backend address
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const socket = io(API_URL, {
    path: "/ws/socket.io",
    auth: { token },
    autoConnect: true,
  });
  return socket;
}
