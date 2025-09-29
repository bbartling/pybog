"""
FastAPI Integration Example for PyBOG Agent

Shows how to integrate the PyBOG agent with FastAPI endpoints
and WebSocket connections for real-time streaming.
"""

import asyncio
import json
from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from backend.core.events import EventBus, Event
from backend.services.pybog_agent import PyBOGAgent


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str


class AnalysisRequest(BaseModel):
    content: str
    session_id: str


class ChatResponse(BaseModel):
    status: str
    message: str


# Create FastAPI app
app = FastAPI(title="PyBOG Agent API", version="1.0.0")

# Global instances
event_bus = EventBus()
agent = PyBOGAgent(event_bus)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Subscribe to events for this session
        await event_bus.subscribe(session_id, self._handle_event)
        
        # Send replay events if any
        replay_events = await event_bus.get_replay_events(session_id)
        for event in replay_events:
            await self._send_event_to_websocket(websocket, event)
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def _handle_event(self, event: Event):
        """Handle events from EventBus and send to WebSocket."""
        session_id = event.session_id
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await self._send_event_to_websocket(websocket, event)
    
    async def _send_event_to_websocket(self, websocket: WebSocket, event: Event):
        """Send event to WebSocket as JSON."""
        try:
            message = {
                "type": event.type,
                "session_id": event.session_id,
                "operation": event.operation,
                "data": event.data,
                "timestamp": event.timestamp.isoformat()
            }
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")


manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "chat":
                    # Process chat message
                    await agent.process_chat_message(
                        session_id, 
                        message.get("content", "")
                    )
                
                elif message.get("type") == "analyze":
                    # Process document analysis
                    await agent.analyze_document_content(
                        session_id,
                        message.get("content", "")
                    )
                
                elif message.get("type") == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": event.timestamp.isoformat()
                    }))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """HTTP endpoint for chat (non-streaming)."""
    try:
        # Process chat message (events will be emitted to EventBus)
        await agent.process_chat_message(request.session_id, request.message)
        
        return ChatResponse(
            status="success",
            message="Chat message processed. Connect to WebSocket for streaming responses."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_endpoint(request: AnalysisRequest):
    """HTTP endpoint for document analysis."""
    try:
        # Perform analysis
        result = await agent.analyze_document_content(
            request.session_id, 
            request.content
        )
        
        return {
            "status": "success",
            "analysis": result
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    try:
        history = agent.get_session_history(session_id)
        
        # Convert LangChain messages to serializable format
        serializable_history = []
        for msg in history:
            if hasattr(msg, 'content'):
                serializable_history.append({
                    "type": msg.__class__.__name__,
                    "content": msg.content
                })
        
        return {
            "session_id": session_id,
            "history": serializable_history
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}/history")
async def clear_session_history(session_id: str):
    """Clear conversation history for a session."""
    try:
        agent.clear_session_history(session_id)
        await event_bus.clear_session(session_id)
        
        return {
            "status": "success",
            "message": f"Session {session_id} history cleared"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_active_sessions():
    """List all active sessions."""
    try:
        agent_sessions = agent.get_active_sessions()
        eventbus_sessions = event_bus.get_session_count()
        
        return {
            "agent_sessions": agent_sessions,
            "eventbus_session_count": eventbus_sessions,
            "websocket_connections": list(manager.active_connections.keys())
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None,
        "eventbus_initialized": event_bus is not None,
        "active_sessions": len(agent.get_active_sessions()),
        "websocket_connections": len(manager.active_connections)
    }


if __name__ == "__main__":
    import uvicorn
    
    print("Starting PyBOG Agent FastAPI Integration Example")
    print("Available endpoints:")
    print("  WebSocket: ws://localhost:8000/ws/{session_id}")
    print("  Chat: POST /api/chat")
    print("  Analysis: POST /api/analyze")
    print("  History: GET /api/sessions/{session_id}/history")
    print("  Health: GET /health")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)