"""
Example usage of FileService with hybrid storage and EventBus integration.
Demonstrates file upload, storage decision logic, and state transitions.
"""

import asyncio
import tempfile
from pathlib import Path

from core.events import EventBus
from services.file_service import FileService
from models.file_models import FileType, ProgressState


class MockUploadFile:
    """Mock UploadFile for demonstration."""
    
    def __init__(self, filename: str, content: bytes, content_type: str = "text/plain"):
        self.filename = filename
        self.content = content
        self.content_type = content_type
    
    async def read(self) -> bytes:
        return self.content


async def demonstrate_file_service():
    """Demonstrate FileService functionality."""
    
    print("🚀 FileService Demonstration")
    print("=" * 50)
    
    # Create EventBus and FileService
    event_bus = EventBus()
    file_service = FileService(event_bus)
    
    # Set up event listener to show events
    async def event_listener(event):
        print(f"📡 Event: {event.type} | Operation: {event.operation} | Data: {event.data}")
    
    await event_bus.subscribe("demo-session", event_listener)
    
    print("\n1. Testing Small File Upload (BYTEA Storage)")
    print("-" * 40)
    
    # Create small file (will use BYTEA storage)
    small_content = b"This is a small file that will be stored as BYTEA in the database."
    small_file = MockUploadFile("small_document.txt", small_content, "text/plain")
    
    try:
        # Note: This would fail in real usage without a database connection
        # but demonstrates the API
        print(f"📁 Uploading small file: {small_file.filename} ({len(small_content)} bytes)")
        print(f"💾 Expected storage: BYTEA (< 10MB)")
        
        # In real usage:
        # result = await file_service.upload_file("demo-session", small_file)
        # print(f"✅ Upload successful: File ID {result.id}, Storage: {result.storage_type}")
        
    except Exception as e:
        print(f"⚠️  Expected error (no database): {e}")
    
    print("\n2. Testing Large File Upload (File Path Storage)")
    print("-" * 40)
    
    # Create large file (will use file_path storage)
    large_content = b"X" * (11 * 1024 * 1024)  # 11MB
    large_file = MockUploadFile("large_document.pdf", large_content, "application/pdf")
    
    try:
        print(f"📁 Uploading large file: {large_file.filename} ({len(large_content)} bytes)")
        print(f"💾 Expected storage: FILE_PATH (>= 10MB)")
        
        # In real usage:
        # result = await file_service.upload_file("demo-session", large_file)
        # print(f"✅ Upload successful: File ID {result.id}, Storage: {result.storage_type}")
        
    except Exception as e:
        print(f"⚠️  Expected error (no database): {e}")
    
    print("\n3. Testing File Size Limit")
    print("-" * 40)
    
    # Create extremely large file (will be rejected)
    huge_content = b"X" * (51 * 1024 * 1024)  # 51MB
    huge_file = MockUploadFile("huge_file.bin", huge_content, "application/octet-stream")
    
    try:
        print(f"📁 Uploading huge file: {huge_file.filename} ({len(huge_content)} bytes)")
        print(f"🚫 Expected result: REJECTED (> 50MB limit)")
        
        # This should fail even without database
        await file_service.upload_file("demo-session", huge_file)
        
    except ValueError as e:
        print(f"✅ Correctly rejected: {e}")
    except Exception as e:
        print(f"⚠️  Other error: {e}")
    
    print("\n4. State Transition Validation")
    print("-" * 40)
    
    # Demonstrate state transition validation
    print("🔄 Valid state transitions:")
    try:
        file_service._validate_state_transition(ProgressState.QUEUED, ProgressState.PROCESSING)
        print("  ✅ QUEUED → PROCESSING")
        
        file_service._validate_state_transition(ProgressState.PROCESSING, ProgressState.FINALIZING)
        print("  ✅ PROCESSING → FINALIZING")
        
        file_service._validate_state_transition(ProgressState.FINALIZING, ProgressState.COMPLETE)
        print("  ✅ FINALIZING → COMPLETE")
        
        file_service._validate_state_transition(ProgressState.FAILED, ProgressState.QUEUED)
        print("  ✅ FAILED → QUEUED (retry)")
        
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
    
    print("\n🚫 Invalid state transitions:")
    try:
        file_service._validate_state_transition(ProgressState.COMPLETE, ProgressState.PROCESSING)
        print("  ❌ Should have failed!")
    except ValueError as e:
        print(f"  ✅ Correctly rejected: COMPLETE → PROCESSING")
    
    try:
        file_service._validate_state_transition(ProgressState.QUEUED, ProgressState.COMPLETE)
        print("  ❌ Should have failed!")
    except ValueError as e:
        print(f"  ✅ Correctly rejected: QUEUED → COMPLETE")
    
    print("\n5. Event Bus Functionality")
    print("-" * 40)
    
    # Demonstrate event publishing and replay
    print("📡 Publishing test events...")
    
    from core.events import Event
    from datetime import datetime, timezone
    
    test_events = [
        Event(
            type="progress",
            session_id="demo-session",
            operation="upload",
            data={"state": "queued", "message": "File queued for upload"}
        ),
        Event(
            type="progress", 
            session_id="demo-session",
            operation="upload",
            data={"state": "processing", "message": "Uploading file"}
        ),
        Event(
            type="progress",
            session_id="demo-session", 
            operation="upload",
            data={"state": "complete", "message": "Upload completed"}
        )
    ]
    
    for event in test_events:
        await event_bus.publish("demo-session", event)
        await asyncio.sleep(0.1)  # Small delay to see events
    
    print("\n📚 Event replay buffer:")
    replay_events = await event_bus.get_replay_events("demo-session")
    for i, event in enumerate(replay_events, 1):
        print(f"  {i}. {event.type} | {event.operation} | {event.data.get('state', 'N/A')}")
    
    print(f"\n📊 EventBus Stats:")
    print(f"  - Active sessions: {event_bus.get_session_count()}")
    print(f"  - Queue size: {event_bus.get_queue_size('demo-session')}")
    print(f"  - Replay buffer size: {event_bus.get_replay_buffer_size('demo-session')}")
    print(f"  - Subscribers: {event_bus.get_subscriber_count('demo-session')}")
    
    print("\n✨ FileService Demonstration Complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(demonstrate_file_service())