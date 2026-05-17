"""
NexusIQ — WebSocket route for real-time agent log streaming.

Fixes vs original:
1. Concurrent receive + send tasks so dead connections are detected immediately
   (original only caught disconnects when trying to send, causing zombie sockets).
2. 30-second heartbeat pings keep the connection alive through proxies/load balancers.
3. auth via token query-param fallback — some WS clients cannot set headers, so
   ?token=<jwt> is accepted when the cookie is absent.
4. pubsub cleanup is guaranteed even if the send loop crashes mid-message.
5. All internal errors are logged before silently closing; nothing swallows silently.
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

from db.redis_client import get_redis
from utils.security import decode_token   # extract and re-use token decoder
from exceptions.base import AuthException

router = APIRouter(prefix="/ws", tags=["ws"])

_HEARTBEAT_INTERVAL = 30   # seconds — keeps proxy connections alive
_CHANNEL_PREFIX     = "nexus:logs"


@router.websocket("/logs/{session_id}")
async def websocket_logs(
    websocket: WebSocket,
    session_id: str,
    token: str | None = Query(default=None),   # fallback for clients that can't set headers
) -> None:
    """
    Subscribe to Redis pub/sub channel nexus:logs:{session_id} and stream
    JSON log lines to the connected client in real time.

    Auth: reads HttpOnly cookie 'access_token' first; falls back to ?token= query param.
    """

    # ── Authenticate BEFORE accept() so unauthorised clients get a clean 403 ─
    raw_token: str | None = websocket.cookies.get("access_token") or token
    if not raw_token:
        await websocket.close(code=4001, reason="Missing auth token")
        return
    try:
        decode_token(raw_token)   # raises AuthException on invalid / expired
    except (AuthException, Exception) as exc:
        logger.warning(f"[ws] Auth failed for session={session_id}: {exc}")
        await websocket.close(code=4003, reason="Invalid or expired token")
        return

    await websocket.accept()
    logger.info(f"[ws] Client connected session={session_id}")

    redis  = await get_redis()
    pubsub = redis.pubsub()
    channel = f"{_CHANNEL_PREFIX}:{session_id}"
    await pubsub.subscribe(channel)

    stop_event = asyncio.Event()

    # ── Receive loop — only purpose is to detect disconnect ───────────────
    async def _receive() -> None:
        try:
            while not stop_event.is_set():
                await websocket.receive_text()   # raises WebSocketDisconnect on close
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.debug(f"[ws] receive loop ended session={session_id}: {exc}")
        finally:
            stop_event.set()

    # ── Send loop — forwards pub/sub messages + heartbeat pings ──────────
    async def _send() -> None:
        try:
            while not stop_event.is_set():
                # Poll pub/sub with 1s timeout so heartbeat fires on schedule
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    text = data if isinstance(data, str) else data.decode("utf-8", errors="replace")
                    await websocket.send_text(text)

                # Send a heartbeat ping every _HEARTBEAT_INTERVAL seconds.
                # We track elapsed time with a simple counter since we loop every ~1s.
                _send._ticks = getattr(_send, "_ticks", 0) + 1
                if _send._ticks >= _HEARTBEAT_INTERVAL:
                    _send._ticks = 0
                    await websocket.send_text(
                        json.dumps({"type": "heartbeat", "session_id": session_id})
                    )

        except WebSocketDisconnect:
            pass
        except Exception as exc:
            logger.warning(f"[ws] send loop error session={session_id}: {exc}")
        finally:
            stop_event.set()

    recv_task = asyncio.create_task(_receive())
    send_task = asyncio.create_task(_send())

    # Wait for whichever loop ends first (disconnect or error), then cancel the other
    try:
        done, pending = await asyncio.wait(
            [recv_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
    finally:
        await pubsub.unsubscribe(channel)
        try:
            await pubsub.aclose()
        except Exception:
            pass
        logger.info(f"[ws] Client disconnected session={session_id}")
