# Event Bus System

## Overview

The Event Bus system provides in-memory, session-based event communication for the FastAPI backend. It enables services to communicate through events without direct coupling, supporting real-time streaming and session resume functionality.

## Key Features

### ✅ Implemented Features

1. **In-memory EventBus with asyncio.Queue per session**
   - Each session gets its own event queue for isolation
   - Async/await support for non-blocking operations
   - Thread-safe operations with asyncio locks

2. **Event model with required fields**
   - `type`: Event category (chat, progress, bog_generated, error)
   - `session_id`: Session identifier for isolation
   - `operation`: Specific operation (message, upload, analyze, etc.)
   - `data`: Event payload as dictionary
   - `timestamp`: Automatic UTC timestamp

3. **Event replay functionality**
   - `asyncio.deque(maxlen=10)` per session for last 10 events
   - Session resume capability for WebSocket reconnections
   - Replay buffer accessible via `get_replay_events()`

4. **Comprehensive subscription system**
   - Support for both sync and async callbacks
   - Multiple subscribers per session
   - Error handling that doesn't break other subscribers
   - Subscribe/unsubscribe functionality

## Architecture

```
EventBus
├── Session Queues (asyncio.Queue per session)
├── Replay Buffers (deque maxlen=10 per session)  
├── Subscribers (callbacks per session)
└── Thread-safe operations (asyncio.Lock)
```

## Usage Examples

### Basic Publishing and Subscribing

```python
from backend.core.events import Event, EventBus

event_bus = EventBus()

# Subscribe to events
async def handle_event(event):
    print(f"Received: {event.type} - {event.data}")

await event_bus.subscribe("session-1", handle_event)

# Publish an event
event = Event(
    type="chat",
    session_id="session-1", 
    operation="message",
    data={"content": "Hello!"}
)
await event_bus.publish("session-1", event)
```

### Session Resume with Replay

```python
# Get last 10 events for session resume
replay_events = await event_bus.get_replay_events("session-1")

# Process replay events to restore state
for event in replay_events:
    await restore_session_state(event)
```

### Queue-based Event Retrieval

```python
# Get next event (blocking with timeout)
event = await event_bus.get_next_event("session-1", timeout=5.0)
if event:
    await process_event(event)
```

## Testing

Comprehensive unit tests cover:

- ✅ Event creation and serialization
- ✅ Publishing and subscribing
- ✅ Session isolation (events don't cross sessions)
- ✅ Event replay functionality (maxlen=10)
- ✅ Multiple subscribers per session
- ✅ Sync and async callback support
- ✅ Error handling in callbacks
- ✅ Timeout behavior
- ✅ Session cleanup
- ✅ Concurrent publishing
- ✅ Realistic session resume scenarios

Run tests with:
```bash
cd backend
python -m pytest core/test_events.py -v
```

## Integration with Services

Services should emit events rather than handle WebSocket I/O directly:

```python
class FileService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def upload_file(self, session_id: str, file_data: bytes):
        # Emit progress event
        await self.event_bus.publish(session_id, Event(
            type="progress",
            session_id=session_id,
            operation="upload", 
            data={"state": "processing", "file_size": len(file_data)}
        ))
        
        # Process file...
        
        # Emit completion event
        await self.event_bus.publish(session_id, Event(
            type="progress",
            session_id=session_id,
            operation="upload",
            data={"state": "complete", "file_id": file_id}
        ))
```

## Requirements Satisfied

- **4.1**: ✅ Event-driven service communication
- **4.4**: ✅ Session-based event isolation  
- **4.5**: ✅ Event replay for session resume

## Next Steps

The EventBus is ready for integration with:
- WebSocket Manager (consumes events, sends to clients)
- File Service (emits upload/processing events)
- Analysis Engine (emits analysis progress events)
- LangChain Agent (emits chat response events)