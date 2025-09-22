import os, time, json
from fastapi import FastAPI
import socketio
import redis.asyncio as aioredis
from . import auth, utils, celery_worker

# Redis client
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

# Socket.IO server with Redis manager
mgr = socketio.AsyncRedisManager(REDIS_URL)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*", client_manager=mgr)
fastapi_app = FastAPI()
fastapi_app.include_router(auth.router)

app = socketio.ASGIApp(sio, fastapi_app, socketio_path="/ws/socket.io")

async def authenticate_socket(token: str):
    payload = utils.decode_token(token)
    if not payload or "sub" not in payload:
        return None
    return payload["sub"]

@sio.event
async def connect(sid, environ, auth):
    token = auth.get("token") if isinstance(auth, dict) else None
    user = await authenticate_socket(token) if token else None
    if not user:
        raise ConnectionRefusedError("unauthorized")
    await sio.save_session(sid, {"username": user})
    print("Connected:", user)

@sio.event
async def send_message(sid, data):
    sess = await sio.get_session(sid)
    user = sess["username"]
    room = data.get("room", "global")
    text = data.get("text", "")

    msg = {"user": user, "room": room, "text": text, "ts": int(time.time())}

    await redis.lpush(f"chat:{room}", json.dumps(msg))
    await redis.ltrim(f"chat:{room}", 0, 99)

    sio.start_background_task(celery_worker.save_message.delay, user, room, text)

    await sio.emit("new_message", msg, room=room)
