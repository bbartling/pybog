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
from typing import Any, Dict, List, Optional

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


# Lazy Redis connection (module-level singleton)
_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# Resume URL storage ---------------------------------------------------------

async def store_resume_url(session_id: str, resume_url: str) -> None:
    """Persist the n8n Wait node resume webhook URL for a session."""
    r = await get_redis()
    await r.set(_resume_key(session_id), resume_url)
    logger.info("Stored resume URL for session %s", session_id)


async def get_resume_url(session_id: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(_resume_key(session_id))


# Message storage (polling fallback) ----------------------------------------

async def append_message(session_id: str, message: Dict[str, Any]) -> None:
    r = await get_redis()
    await r.rpush(_messages_key(session_id), json.dumps(message))


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
            return result
    except httpx.RequestError as e:
        logger.error("Failed to POST resume webhook: %s", e)
        return {"success": False, "error": str(e)}
