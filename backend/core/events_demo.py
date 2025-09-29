"""
Demo script showing how to use the EventBus system.

This demonstrates the key features:
- Publishing and subscribing to events
- Session isolation
- Event replay for session resume
- Multiple subscribers
"""

import asyncio
from events import Event, EventBus


async def demo_basic_usage():
    """Demonstrate basic event publishing and subscribing."""
    print("=== Basic Event Bus Demo ===")
    
    event_bus = EventBus()
    session_id = "demo-session"
    
    # Create a subscriber
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
        print(f"Received: {event.type} - {event.operation} - {event.data}")
    
    # Subscribe to events
    await event_bus.subscribe(session_id, event_handler)
    
    # Publish some events
    events = [
        Event(type="chat", session_id=session_id, operation="message", 
              data={"content": "Hello, world!"}),
        Event(type="progress", session_id=session_id, operation="upload", 
              data={"state": "processing", "file_id": 1}),
        Event(type="bog_generated", session_id=session_id, operation="analyze", 
              data={"file_id": 2, "analysis": {"quality": 0.85}})
    ]
    
    for event in events:
        await event_bus.publish(session_id, event)
        await asyncio.sleep(0.1)  # Small delay to see events in order
    
    print(f"Total events received: {len(received_events)}")
    print()


async def demo_session_isolation():
    """Demonstrate that sessions are isolated from each other."""
    print("=== Session Isolation Demo ===")
    
    event_bus = EventBus()
    
    # Create handlers for different sessions
    session1_events = []
    session2_events = []
    
    def session1_handler(event):
        session1_events.append(event)
        print(f"Session 1 received: {event.data}")
    
    def session2_handler(event):
        session2_events.append(event)
        print(f"Session 2 received: {event.data}")
    
    # Subscribe to different sessions
    await event_bus.subscribe("session-1", session1_handler)
    await event_bus.subscribe("session-2", session2_handler)
    
    # Publish to different sessions
    await event_bus.publish("session-1", Event(
        type="chat", session_id="session-1", operation="message",
        data={"content": "Message for session 1"}
    ))
    
    await event_bus.publish("session-2", Event(
        type="chat", session_id="session-2", operation="message",
        data={"content": "Message for session 2"}
    ))
    
    await asyncio.sleep(0.1)
    
    print(f"Session 1 events: {len(session1_events)}")
    print(f"Session 2 events: {len(session2_events)}")
    print()


async def demo_event_replay():
    """Demonstrate event replay functionality for session resume."""
    print("=== Event Replay Demo ===")
    
    event_bus = EventBus()
    session_id = "replay-session"
    
    # Publish several events
    print("Publishing events...")
    for i in range(5):
        event = Event(
            type="progress", session_id=session_id, operation="workflow",
            data={"step": i, "message": f"Processing step {i}"}
        )
        await event_bus.publish(session_id, event)
    
    # Get replay events (simulating session resume)
    replay_events = await event_bus.get_replay_events(session_id)
    
    print(f"Replay buffer contains {len(replay_events)} events:")
    for event in replay_events:
        print(f"  - Step {event.data['step']}: {event.data['message']}")
    
    print()


async def demo_queue_operations():
    """Demonstrate queue-based event retrieval."""
    print("=== Queue Operations Demo ===")
    
    event_bus = EventBus()
    session_id = "queue-session"
    
    # Publish events
    await event_bus.publish(session_id, Event(
        type="chat", session_id=session_id, operation="message",
        data={"content": "First message"}
    ))
    
    await event_bus.publish(session_id, Event(
        type="chat", session_id=session_id, operation="message",
        data={"content": "Second message"}
    ))
    
    # Retrieve events from queue
    print("Retrieving events from queue:")
    
    event1 = await event_bus.get_next_event(session_id, timeout=1.0)
    if event1:
        print(f"Got event 1: {event1.data['content']}")
    
    event2 = await event_bus.get_next_event(session_id, timeout=1.0)
    if event2:
        print(f"Got event 2: {event2.data['content']}")
    
    # Try to get another event (should timeout)
    event3 = await event_bus.get_next_event(session_id, timeout=0.1)
    if event3 is None:
        print("No more events (timeout)")
    
    print()


async def main():
    """Run all demos."""
    await demo_basic_usage()
    await demo_session_isolation()
    await demo_event_replay()
    await demo_queue_operations()
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())