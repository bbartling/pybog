from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import os
import httpx

from ..n8n_resume import resume_workflow, list_messages, append_message

router = APIRouter(prefix="/api", tags=["conversation"])


class FeedbackPayload(BaseModel):
    feedback: Optional[str] = None


@router.post("/session/{session_id}/approve")
async def approve_session(session_id: str, payload: FeedbackPayload | None = None):
    """Resume a paused n8n workflow with an approval signal."""
    feedback = (payload.feedback if payload else None)
    await append_message(
        session_id,
        {
            "type": "user_action",
            "action": "approved",
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    result = await resume_workflow(
        session_id,
        {"action": "approved", "feedback": feedback, "sessionId": session_id},
    )
    if not result.get("success"):
        # Fallback: call main webhook with approve action if no resume URL is stored
        n8n_url = os.getenv("N8N_URL", "http://n8n:5678")
        webhook = f"{n8n_url}/webhook/pybog-main"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(webhook, json={
                "sessionId": session_id,
                "action": "approve",
                "feedback": feedback or ""
            })
            if not (200 <= resp.status_code < 300):
                raise HTTPException(status_code=502, detail=f"Fallback webhook failed: {resp.text}")
            return {"status": "resumed", "sessionId": session_id, "result": {"success": True, "fallback": True, "body": resp.json()}}
    return {"status": "resumed", "sessionId": session_id, "result": result}


@router.post("/session/{session_id}/request-changes")
async def request_changes(session_id: str, payload: FeedbackPayload | None = None):
    """Resume a paused n8n workflow with a change-request signal and feedback."""
    feedback = (payload.feedback if payload else None)
    await append_message(
        session_id,
        {
            "type": "user_action",
            "action": "changes_requested",
            "feedback": feedback,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    result = await resume_workflow(
        session_id,
        {"action": "changes_requested", "feedback": feedback, "sessionId": session_id},
    )
    if not result.get("success"):
        # Fallback: call main webhook with refine action
        n8n_url = os.getenv("N8N_URL", "http://n8n:5678")
        webhook = f"{n8n_url}/webhook/pybog-main"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(webhook, json={
                "sessionId": session_id,
                "action": "refine",
                "feedback": feedback or ""
            })
            if not (200 <= resp.status_code < 300):
                raise HTTPException(status_code=502, detail=f"Fallback webhook failed: {resp.text}")
            return {"status": "resumed", "sessionId": session_id, "result": {"success": True, "fallback": True, "body": resp.json()}}
    return {"status": "resumed", "sessionId": session_id, "result": result}


@router.get("/session/{session_id}/messages")
async def get_session_messages(session_id: str, limit: int = Query(100, ge=1, le=500)):
    """Polling fallback to retrieve recent chat messages for a session."""
    msgs = await list_messages(session_id, limit=limit)
    return {"sessionId": session_id, "messages": msgs}
