"""
Utilities to store and resume n8n workflows waiting on a Wait node via resume webhook URLs.

- Stores the per-session resume webhook URL (provided by n8n) in Redis
- Exposes helpers to append/list chat messages per session (polling fallback)
- Resumes a waiting workflow by POSTing payloads to the stored resume URL
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, AsyncGenerator

import httpx
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

# Environment configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Redis key helpers
_DEF_NS = "pybog"


def _resume_key(session_id: str) -> str:
    return f"{_DEF_NS}:session:{session_id}:resume_url"


def _messages_key(session_id: str) -> str:
    return f"{_DEF_NS}:session:{session_id}:messages"


def _events_channel(session_id: str) -> str:
    return f"{_DEF_NS}:session:{session_id}:events"


# Lazy Redis connection (module-level singleton)
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def _publish_event(session_id: str, event: Dict[str, Any]) -> None:
    r = await get_redis()
    try:
        await r.publish(_events_channel(session_id), json.dumps(event))
    except Exception:
        logger.debug("Failed to publish event for session %s", session_id)


# Resume URL storage ---------------------------------------------------------

async def store_resume_url(session_id: str, resume_url: str) -> None:
    """Persist the n8n Wait node resume webhook URL for a session."""
    r = await get_redis()
    await r.set(_resume_key(session_id), resume_url)
    logger.info("Stored resume URL for session %s", session_id)
    await _publish_event(session_id, {"type": "resume_url_stored", "resume_url": resume_url})


async def get_resume_url(session_id: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(_resume_key(session_id))


# Message storage (polling + streaming) -------------------------------------

async def append_message(session_id: str, message: Dict[str, Any]) -> None:
    r = await get_redis()
    await r.rpush(_messages_key(session_id), json.dumps(message))
    await _publish_event(session_id, {"type": "message", **message})


async def list_messages(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    r = await get_redis()
    # Get last N messages
    total = await r.llen(_messages_key(session_id))
    start = max(0, total - limit)
    raw = await r.lrange(_messages_key(session_id), start, total)
    out: List[Dict[str, Any]] = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except Exception:
            out.append({"type": "text", "content": str(item)})
    return out


async def event_stream(session_id: str) -> AsyncGenerator[str, None]:
    """Server-Sent Events (SSE) generator for live session updates."""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_events_channel(session_id))
    # Emit an initial comment to open the stream
    yield ":ok\n\n"
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            if msg and msg.get("type") == "message":
                data = msg.get("data")
                yield f"data: {data}\n\n"
            else:
                # keep-alive
                yield ":keepalive\n\n"
    finally:
        try:
            await pubsub.unsubscribe(_events_channel(session_id))
            await pubsub.close()
        except Exception:
            pass


# Resume workflow ------------------------------------------------------------

async def resume_workflow(session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST the given payload to the stored resume webhook URL to continue the paused
    n8n workflow execution.
    """
    url = await get_resume_url(session_id)
    if not url:
        msg = f"No resume URL stored for session {session_id}"
        logger.error(msg)
        return {"success": False, "error": msg}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            ok = 200 <= resp.status_code < 300
            body = {}
            try:
                body = resp.json()
            except Exception:
                body = {"text": resp.text}
            result = {
                "success": ok,
                "status": resp.status_code,
                "body": body,
            }
            if not ok:
                logger.error("Resume webhook error (%s): %s", resp.status_code, resp.text)
            else:
                await _publish_event(session_id, {"type": "resumed", "payload": payload, "status": resp.status_code})
            return result
    except httpx.RequestError as e:
        logger.error("Failed to POST resume webhook: %s", e)
        return {"success": False, "error": str(e)}
