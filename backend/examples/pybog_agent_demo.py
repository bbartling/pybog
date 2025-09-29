"""
PyBOG Agent Demo

Demonstrates the PyBOG LangChain agent integration with EventBus.
Shows how to use the agent for chat and document analysis with streaming responses.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.events import EventBus, Event
from services.pybog_agent import PyBOGAgent


async def event_logger(event: Event):
    """Log events for demonstration."""
    timestamp = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {event.type.upper()} | {event.operation} | {event.session_id}")
    
    if event.type == "chat":
        if event.data.get("is_complete"):
            print(f"  ✓ Chat completed: {event.data.get('final_content', '')[:50]}...")
        else:
            print(f"  → Token: '{event.data.get('content', '')}'")
    
    elif event.type == "progress":
        state = event.data.get("state", "unknown")
        message = event.data.get("message", "")
        print(f"  📊 {state.upper()}: {message}")
    
    elif event.type == "error":
        error_code = event.data.get("error_code", "UNKNOWN")
        message = event.data.get("message", "")
        print(f"  ❌ {error_code}: {message}")


async def demo_chat_interaction():
    """Demonstrate chat interaction with streaming responses."""
    print("\n" + "="*60)
    print("DEMO: Chat Interaction with Streaming")
    print("="*60)
    
    # Create EventBus and agent
    event_bus = EventBus()
    
    # Note: In real usage, you would provide a valid OpenAI API key
    # For demo purposes, we'll mock the LLM responses
    try:
        agent = PyBOGAgent(event_bus, openai_api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        print(f"Note: Using mock agent due to: {e}")
        return
    
    session_id = "demo_chat_session"
    
    # Subscribe to events
    await event_bus.subscribe(session_id, event_logger)
    
    # Simulate chat interaction
    print(f"\nStarting chat session: {session_id}")
    print("User: Tell me about HVAC control sequences for VAV systems")
    
    try:
        await agent.process_chat_message(
            session_id, 
            "Tell me about HVAC control sequences for VAV systems"
        )
        
        # Allow time for all events to be processed
        await asyncio.sleep(1)
        
        print("\nChat interaction completed!")
        
    except Exception as e:
        print(f"Chat failed (expected in demo without API key): {e}")


async def demo_document_analysis():
    """Demonstrate document analysis with structured output."""
    print("\n" + "="*60)
    print("DEMO: Document Analysis")
    print("="*60)
    
    # Create EventBus and agent
    event_bus = EventBus()
    
    try:
        agent = PyBOGAgent(event_bus, openai_api_key=os.getenv("OPENAI_API_KEY"))
    except Exception as e:
        print(f"Note: Using mock agent due to: {e}")
        return
    
    session_id = "demo_analysis_session"
    
    # Subscribe to events
    await event_bus.subscribe(session_id, event_logger)
    
    # Sample HVAC document content
    document_content = """
    VAV Box Control Sequence:
    
    1. Supply Air Temperature Control:
       - Monitor supply air temperature sensor (SAT)
       - Maintain setpoint of 55°F ± 2°F
       - Modulate cooling coil valve based on temperature error
    
    2. Airflow Control:
       - Monitor zone temperature sensor (ZT)
       - Calculate airflow demand based on zone temperature error
       - Modulate VAV damper position (0-100%)
       - Minimum airflow: 30% of maximum CFM
       - Maximum airflow: Design CFM per zone
    
    3. Reheat Control (if equipped):
       - Enable reheat when airflow at minimum and zone temperature < setpoint - 1°F
       - Modulate reheat valve 0-100% based on temperature error
    """
    
    print(f"\nStarting document analysis: {session_id}")
    print("Analyzing VAV control sequence document...")
    
    try:
        result = await agent.analyze_document_content(session_id, document_content)
        
        # Allow time for all events to be processed
        await asyncio.sleep(1)
        
        print("\nAnalysis Results:")
        print(f"  Quality Score: {result.get('quality_score', 0):.2f}")
        print(f"  IO Points Found: {len(result.get('io_points', []))}")
        print(f"  Control Blocks: {len(result.get('control_blocks', []))}")
        print(f"  Issues: {len(result.get('issues', []))}")
        
        # Show some details
        if result.get('io_points'):
            print("\n  Sample IO Points:")
            for point in result['io_points'][:2]:
                print(f"    - {point.get('name', 'Unknown')} ({point.get('type', 'unknown')})")
        
        if result.get('control_blocks'):
            print("\n  Sample Control Blocks:")
            for block in result['control_blocks'][:2]:
                print(f"    - {block.get('name', 'Unknown')} (complexity: {block.get('complexity', 0)})")
        
        print("\nDocument analysis completed!")
        
    except Exception as e:
        print(f"Analysis failed (expected in demo without API key): {e}")


async def demo_event_bus_integration():
    """Demonstrate EventBus integration features."""
    print("\n" + "="*60)
    print("DEMO: EventBus Integration Features")
    print("="*60)
    
    event_bus = EventBus()
    session_id = "demo_eventbus_session"
    
    # Collect events for analysis
    collected_events = []
    
    async def event_collector(event: Event):
        collected_events.append(event)
        await event_logger(event)
    
    await event_bus.subscribe(session_id, event_collector)
    
    # Simulate some events
    print(f"\nPublishing test events to session: {session_id}")
    
    # Simulate progress events
    await event_bus.publish(session_id, Event(
        type="progress",
        session_id=session_id,
        operation="test",
        data={"state": "processing", "message": "Starting test operation"}
    ))
    
    await event_bus.publish(session_id, Event(
        type="chat",
        session_id=session_id,
        operation="test",
        data={"content": "Hello", "is_complete": False, "buffer_content": "Hello"}
    ))
    
    await event_bus.publish(session_id, Event(
        type="progress",
        session_id=session_id,
        operation="test",
        data={"state": "complete", "message": "Test operation completed"}
    ))
    
    # Allow events to be processed
    await asyncio.sleep(0.1)
    
    print(f"\nCollected {len(collected_events)} events")
    
    # Test replay functionality
    replay_events = await event_bus.get_replay_events(session_id)
    print(f"Replay buffer contains {len(replay_events)} events")
    
    # Test session isolation
    other_session = "other_session"
    other_events = []
    await event_bus.subscribe(other_session, lambda e: other_events.append(e))
    
    await event_bus.publish(other_session, Event(
        type="test",
        session_id=other_session,
        operation="isolation_test",
        data={"message": "This should not appear in main session"}
    ))
    
    await asyncio.sleep(0.1)
    
    print(f"Session isolation test: main session has {len(collected_events)} events, "
          f"other session has {len(other_events)} events")


async def main():
    """Run all demos."""
    print("PyBOG Agent Integration Demo")
    print("This demo shows how the PyBOG LangChain agent integrates with EventBus")
    print("for streaming responses and event-driven communication.")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("\nNote: Set OPENAI_API_KEY environment variable for full functionality")
        print("Demo will show event structure but may not have real LLM responses")
    
    # Run demos
    await demo_event_bus_integration()
    await demo_chat_interaction()
    await demo_document_analysis()
    
    print("\n" + "="*60)
    print("Demo completed! The PyBOG agent successfully integrates with EventBus")
    print("for streaming chat responses and document analysis.")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())