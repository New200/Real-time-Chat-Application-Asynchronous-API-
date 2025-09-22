# main.py
import os
import time
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt, JWTError
import socketio
import redis.asyncio as aioredis

# Config (set via env in production)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory users (demo). Replace with real DB in production.
users = {}  # username -> {"username", "hashed_password"}

def hash_password(pw: str):
    return pwd_context.hash(pw)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_seconds: Optional[int] = None):
    to_encode = data.copy()
    if expires_seconds:
        to_encode.update({"exp": time.time() + expires_seconds})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# Redis client (async)
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

# Socket.IO server (async)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
fastapi_app = FastAPI()

# Socket.IO ASGI app that wraps FastAPI
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app, socketio_path="/ws/socket.io")

# --- REST endpoints for signup/login (very small demo) ---
@fastapi_app.post("/register")
async def register(form: OAuth2PasswordRequestForm = Depends()):
    # form.username, form.password
    if form.username in users:
        raise HTTPException(status_code=400, detail="User exists")
    users[form.username] = {
        "username": form.username,
        "hashed_password": hash_password(form.password),
    }
    return {"msg": "registered"}

@fastapi_app.post("/token")
async def login_for_access_token(form: OAuth2PasswordRequestForm = Depends()):
    u = users.get(form.username)
    if not u or not verify_password(form.password, u["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect credentials")
    token = create_access_token({"sub": u["username"]}, expires_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return {"access_token": token, "token_type": "bearer"}

# --- Socket.IO logic ---
async def authenticate_socket(token: str):
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    username = payload["sub"]
    if username not in users:
        return None
    return users[username]

@sio.event
async def connect(sid, environ, auth):
    # client should pass { auth: { token: "..."} } when connecting
    token = None
    if isinstance(auth, dict):
        token = auth.get("token")
    user = await authenticate_socket(token) if token else None
    if not user:
        raise ConnectionRefusedError("authentication failed")
    # Save small session
    await sio.save_session(sid, {"username": user["username"]})
    print("connected:", user["username"])

@sio.event
async def disconnect(sid):
    sess = await sio.get_session(sid)
    if sess:
        print("disconnected:", sess.get("username"))

# rate limit example: allow up to 5 messages per second
async def rate_limit_check(username: str, limit=5, window_seconds=1):
    key = f"rl:{username}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)
    return count <= limit

@sio.event
async def send_message(sid, data):
    """
    data example: {"room": "general", "text": "hello"}
    """
    sess = await sio.get_session(sid)
    username = sess.get("username")
    if not await rate_limit_check(username):
        await sio.emit("rate_limited", {"msg": "Too many messages"}, to=sid)
        return

    room = data.get("room", "global")
    msg = {
        "user": username,
        "text": data.get("text"),
        "ts": int(time.time())
    }

    # persist in Redis list for quick retrieval
    await redis.lpush(f"chat:{room}", json.dumps(msg))
    # trim to last 100 messages
    await redis.ltrim(f"chat:{room}", 0, 99)

    # Broadcast to room
    await sio.emit("new_message", msg, room=room)

# helper endpoint to read last 50 messages (REST)
@fastapi_app.get("/history/{room}")
async def get_history(room: str):
    items = await redis.lrange(f"chat:{room}", 0, 49)
    return [json.loads(x) for x in items]

# you can run with: uvicorn app.main:app --reload --port 8000
