#!/usr/bin/env python3
"""
Session Resume Integration Test
Tests WebSocket session resume functionality in detail
Validates event replay, state restoration, and connection recovery

Requirements: 9.5 - Real-time communication and session resume
"""

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.events import EventBus, Event
from services.websocket_manager import WebSocketManager
from services.session_service import SessionService
from services.workflow_service import WorkflowService
from models.session_models import SessionCreateRequest
from models.workflow_models import ReviewDecision, ReviewRequest

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockWebSocket:
    """Enhanced mock WebSocket for session resume testing"""
    
    def __init__(self, session_id: str, connection_id: str = None):
        self.session_id = session_id
        self.connection_id = connection_id or f"conn-{uuid.uuid4().hex[:8]}"
        self.messages: List[str] = []
        self.closed = False
        self.connected = False
        self.resume_messages: List[str] = []
    
    async def accept(self):
        """Mock accept method"""
        self.connected = True
        logger.info(f"WebSocket {self.connection_id} accepted for session {self.session_id}")
    
    async def send_text(self, text: str):
        """Mock send_text method"""
        if not self.closed:
            self.messages.append(text)
            
            # Track resume messages (messages sent immediately after connection)
            if len(self.messages) <= 10:  # First 10 messages are likely resume messages
                self.resume_messages.append(text)
                
            logger.debug(f"WebSocket {self.connection_id} sent: {text[:100]}...")
    
    async def receive_text(self):
        """Mock receive_text method"""
        return json.dumps({
            "type": "chat",
            "content": f"Hello from {self.connection_id}"
        })
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Mock close method"""
        self.closed = True
        self.connected = False
        logger.info(f"WebSocket {self.connection_id} closed: {code} - {reason}")


class SessionResumeTest:
    """Session resume integration test suite"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.websocket_manager = WebSocketManager(self.event_bus)
        self.session_service = SessionService(self.event_bus)
        self.workflow_service = WorkflowService(self.event_bus)
        
        self.test_sessions: List[str] = []
        self.websockets: Dict[str, MockWebSocket] = {}
    
    async def cleanup(self):
        """Clean up test data"""
        logger.info("Cleaning up session resume test data...")
        
        # Disconnect WebSockets
        for session_id in list(self.websockets.keys()):
            try:
                await self.websocket_manager.disconnect(session_id)
            except Exception as e:
                logger.warning(f"Failed to disconnect WebSocket for {session_id}: {e}")
        
        # Clean up sessions
        for session_id in self.test_sessions:
            try:
                await self.session_service.delete_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to delete test session {session_id}: {e}")
        
        logger.info("Session resume test cleanup completed")
    
    async def create_test_session(self, name: str) -> str:
        """Create a test session"""
        session_id = f"test-resume-{uuid.uuid4().hex[:8]}"
        
        create_request = SessionCreateRequest(
            session_id=session_id,
            name=name,
            metadata={"test": True, "purpose": "session_resume_test"}
        )
        
        session = await self.session_service.create_session(create_request)
        self.test_sessions.append(session_id)
        
        logger.info(f"Created test session: {session_id}")
        return session_id
    
    async def generate_session_activity(self, session_id: str, event_count: int = 10) -> List[Event]:
        """Generate various events for a session to create history"""
        events = []
        
        event_types = [
            ("chat", {"content": "User message", "is_complete": True}),
            ("progress", {"state": "processing", "message": "Processing...", "progress_percent": 25}),
            ("progress", {"state": "processing", "message": "Analyzing...", "progress_percent": 50}),
            ("progress", {"state": "processing", "message": "Generating...", "progress_percent": 75}),
            ("analysis_complete", {"analysis_id": 123, "quality_score": 0.85}),
            ("chat", {"content": "Analysis complete", "is_complete": True}),
            ("file_uploaded", {"file_id": 456, "filename": "test.txt"}),
            ("error", {"error_code": "TEMP", "message": "Temporary error", "retry_possible": True}),
            ("progress", {"state": "complete", "message": "Complete", "progress_percent": 100}),
            ("chat", {"content": "Process finished", "is_complete": True})
        ]
        
        for i in range(min(event_count, len(event_types))):
            event_type, data = event_types[i]
            
            event = Event(
                type=event_type,
                session_id=session_id,
                operation=f"test_operation_{i}",
                data=data,
                metadata={"sequence": i, "test": True}
            )
            
            await self.event_bus.publish(session_id, event)
            events.append(event)
            
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)
        
        logger.info(f"Generated {len(events)} events for session {session_id}")
        return events
    
    async def test_basic_session_resume(self) -> bool:
        """Test basic session resume functionality"""
        logger.info("=== Testing Basic Session Resume ===")
        
        try:
            # Create session and generate activity
            session_id = await self.create_test_session("Basic Resume Test")
            
            # Connect first WebSocket
            ws1 = MockWebSocket(session_id, "ws1")
            await self.websocket_manager.connect(ws1, session_id)
            self.websockets[f"{session_id}_ws1"] = ws1
            
            # Generate session activity
            events = await self.generate_session_activity(session_id, 8)
            
            # Wait for events to be processed
            await asyncio.sleep(0.2)
            
            # Verify first WebSocket received messages
            initial_message_count = len(ws1.messages)
            assert initial_message_count > 0, "First WebSocket should have received messages"
            
            # Disconnect first WebSocket
            await self.websocket_manager.disconnect(session_id)
            assert not self.websocket_manager.is_session_connected(session_id), "Session should be disconnected"
            
            # Connect second WebSocket (resume scenario)
            ws2 = MockWebSocket(session_id, "ws2")
            await self.websocket_manager.connect(ws2, session_id)
            self.websockets[f"{session_id}_ws2"] = ws2
            
            # Wait for resume processing
            await asyncio.sleep(0.3)
            
            # Verify resume messages were sent
            resume_message_count = len(ws2.messages)
            assert resume_message_count > 0, "Resume WebSocket should have received messages"
            
            # Verify resume messages contain event history
            resume_events_found = 0
            for message_text in ws2.messages:
                try:
                    message_data = json.loads(message_text)
                    if message_data.get("type") in ["chat", "progress", "analysis_complete", "file_uploaded"]:
                        resume_events_found += 1
                except json.JSONDecodeError:
                    pass
            
            assert resume_events_found > 0, f"Should have found resume events, found {resume_events_found}"
            
            # Verify session is connected again
            assert self.websocket_manager.is_session_connected(session_id), "Session should be connected after resume"
            
            logger.info(f"✅ Basic session resume test passed!")
            logger.info(f"   Initial messages: {initial_message_count}")
            logger.info(f"   Resume messages: {resume_message_count}")
            logger.info(f"   Resume events found: {resume_events_found}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Basic session resume test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_multiple_reconnections(self) -> bool:
        """Test multiple reconnections and resume consistency"""
        logger.info("=== Testing Multiple Reconnections ===")
        
        try:
            # Create session
            session_id = await self.create_test_session("Multiple Reconnections Test")
            
            # Generate initial activity
            await self.generate_session_activity(session_id, 5)
            
            reconnection_count = 3
            message_counts = []
            
            for i in range(reconnection_count):
                # Connect WebSocket
                ws = MockWebSocket(session_id, f"ws_reconnect_{i}")
                await self.websocket_manager.connect(ws, session_id)
                self.websockets[f"{session_id}_reconnect_{i}"] = ws
                
                # Wait for resume
                await asyncio.sleep(0.2)
                
                # Record message count
                message_count = len(ws.messages)
                message_counts.append(message_count)
                
                # Generate some new activity
                new_event = Event(
                    type="chat",
                    session_id=session_id,
                    operation=f"reconnection_activity_{i}",
                    data={"content": f"Activity during reconnection {i}", "is_complete": True}
                )
                await self.event_bus.publish(session_id, new_event)
                
                # Wait for new event
                await asyncio.sleep(0.1)
                
                # Disconnect
                await self.websocket_manager.disconnect(session_id)
            
            # Verify message counts are consistent (should increase with new activity)
            for i in range(1, len(message_counts)):
                assert message_counts[i] >= message_counts[i-1], f"Message count should not decrease: {message_counts}"
            
            logger.info(f"✅ Multiple reconnections test passed!")
            logger.info(f"   Message counts: {message_counts}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Multiple reconnections test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_concurrent_session_resume(self) -> bool:
        """Test concurrent session resume for multiple sessions"""
        logger.info("=== Testing Concurrent Session Resume ===")
        
        try:
            # Create multiple sessions
            session_count = 3
            sessions = []
            
            for i in range(session_count):
                session_id = await self.create_test_session(f"Concurrent Resume Test {i+1}")
                sessions.append(session_id)
                
                # Generate activity for each session
                await self.generate_session_activity(session_id, 6)
            
            # Connect WebSockets to all sessions
            initial_websockets = []
            for i, session_id in enumerate(sessions):
                ws = MockWebSocket(session_id, f"initial_ws_{i}")
                await self.websocket_manager.connect(ws, session_id)
                initial_websockets.append(ws)
                self.websockets[f"{session_id}_initial"] = ws
            
            # Wait for initial connections
            await asyncio.sleep(0.2)
            
            # Disconnect all sessions
            for session_id in sessions:
                await self.websocket_manager.disconnect(session_id)
            
            # Verify all sessions are disconnected
            for session_id in sessions:
                assert not self.websocket_manager.is_session_connected(session_id), f"Session {session_id} should be disconnected"
            
            # Reconnect all sessions concurrently
            reconnect_tasks = []
            resume_websockets = []
            
            for i, session_id in enumerate(sessions):
                ws = MockWebSocket(session_id, f"resume_ws_{i}")
                resume_websockets.append(ws)
                self.websockets[f"{session_id}_resume"] = ws
                
                task = self.websocket_manager.connect(ws, session_id)
                reconnect_tasks.append(task)
            
            # Wait for all reconnections
            await asyncio.gather(*reconnect_tasks)
            
            # Wait for resume processing
            await asyncio.sleep(0.3)
            
            # Verify all sessions resumed correctly
            for i, (session_id, ws) in enumerate(zip(sessions, resume_websockets)):
                assert self.websocket_manager.is_session_connected(session_id), f"Session {session_id} should be connected"
                assert len(ws.messages) > 0, f"Resume WebSocket {i} should have received messages"
                
                # Verify messages contain correct session ID
                for message_text in ws.messages[:5]:  # Check first 5 messages
                    try:
                        message_data = json.loads(message_text)
                        assert message_data.get("session_id") == session_id, f"Message should have correct session ID"
                    except json.JSONDecodeError:
                        pass
            
            logger.info(f"✅ Concurrent session resume test passed!")
            logger.info(f"   Resumed {len(sessions)} sessions concurrently")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Concurrent session resume test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_resume_with_workflow_state(self) -> bool:
        """Test session resume with active workflow state"""
        logger.info("=== Testing Resume with Workflow State ===")
        
        try:
            # Create session
            session_id = await self.create_test_session("Workflow Resume Test")
            
            # Connect initial WebSocket
            ws1 = MockWebSocket(session_id, "workflow_ws1")
            await self.websocket_manager.connect(ws1, session_id)
            self.websockets[f"{session_id}_workflow1"] = ws1
            
            # Start a workflow
            extracted_text = "Test HVAC control sequence for workflow resume"
            quality_data = {
                "quality_score": 0.8,
                "issues": [],
                "recommendations": ["Test recommendation"],
                "hvac_terms_found": 5
            }
            
            review_id = await self.workflow_service.start_text_extraction_workflow(
                session_id, 1, extracted_text, quality_data
            )
            
            # Wait for workflow messages
            await asyncio.sleep(0.2)
            
            # Verify workflow is active
            status = await self.workflow_service.get_workflow_status(session_id)
            assert status.current_state == "text_review", f"Expected text_review state, got {status.current_state}"
            assert status.pending_reviews_count == 1, "Should have 1 pending review"
            
            # Disconnect WebSocket
            await self.websocket_manager.disconnect(session_id)
            
            # Reconnect with new WebSocket
            ws2 = MockWebSocket(session_id, "workflow_ws2")
            await self.websocket_manager.connect(ws2, session_id)
            self.websockets[f"{session_id}_workflow2"] = ws2
            
            # Wait for resume
            await asyncio.sleep(0.3)
            
            # Verify workflow state is preserved
            resumed_status = await self.workflow_service.get_workflow_status(session_id)
            assert resumed_status.current_state == status.current_state, "Workflow state should be preserved"
            assert resumed_status.pending_reviews_count == status.pending_reviews_count, "Pending reviews should be preserved"
            
            # Verify resume messages include workflow information
            workflow_messages_found = 0
            for message_text in ws2.messages:
                try:
                    message_data = json.loads(message_text)
                    if message_data.get("type") in ["workflow_status", "text_review", "progress"]:
                        workflow_messages_found += 1
                except json.JSONDecodeError:
                    pass
            
            # Continue workflow after resume
            review_request = ReviewRequest(
                session_id=session_id,
                review_id=review_id,
                decision=ReviewDecision.APPROVE,
                feedback="Approved after resume"
            )
            
            response = await self.workflow_service.submit_review(review_request)
            assert response.next_state == "analysis", "Workflow should continue after resume"
            
            logger.info(f"✅ Resume with workflow state test passed!")
            logger.info(f"   Workflow messages found: {workflow_messages_found}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Resume with workflow state test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_resume_message_ordering(self) -> bool:
        """Test that resume messages maintain correct chronological order"""
        logger.info("=== Testing Resume Message Ordering ===")
        
        try:
            # Create session
            session_id = await self.create_test_session("Message Ordering Test")
            
            # Generate events with specific sequence
            ordered_events = []
            for i in range(10):
                event = Event(
                    type="chat",
                    session_id=session_id,
                    operation=f"ordered_message_{i:02d}",
                    data={"content": f"Message {i:02d}", "sequence": i, "is_complete": True}
                )
                await self.event_bus.publish(session_id, event)
                ordered_events.append(event)
                
                # Small delay to ensure different timestamps
                await asyncio.sleep(0.02)
            
            # Connect WebSocket for resume
            ws = MockWebSocket(session_id, "ordering_ws")
            await self.websocket_manager.connect(ws, session_id)
            self.websockets[f"{session_id}_ordering"] = ws
            
            # Wait for resume
            await asyncio.sleep(0.3)
            
            # Extract sequence numbers from resume messages
            sequences = []
            for message_text in ws.messages:
                try:
                    message_data = json.loads(message_text)
                    if message_data.get("type") == "chat" and "data" in message_data:
                        data = message_data["data"]
                        if "sequence" in data:
                            sequences.append(data["sequence"])
                except json.JSONDecodeError:
                    pass
            
            # Verify sequences are in order
            assert len(sequences) > 0, "Should have found sequence numbers in resume messages"
            
            for i in range(1, len(sequences)):
                assert sequences[i] >= sequences[i-1], f"Sequences should be in order: {sequences}"
            
            logger.info(f"✅ Resume message ordering test passed!")
            logger.info(f"   Found {len(sequences)} ordered messages: {sequences}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Resume message ordering test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all session resume tests"""
        logger.info("🚀 Starting Session Resume Integration Tests")
        
        tests = [
            ("Basic Session Resume", self.test_basic_session_resume),
            ("Multiple Reconnections", self.test_multiple_reconnections),
            ("Concurrent Session Resume", self.test_concurrent_session_resume),
            ("Resume with Workflow State", self.test_resume_with_workflow_state),
            ("Resume Message Ordering", self.test_resume_message_ordering),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*60}")
            
            try:
                success = await test_func()
                results.append((test_name, success))
                
                if success:
                    logger.info(f"✅ {test_name} PASSED")
                else:
                    logger.error(f"❌ {test_name} FAILED")
                    
            except Exception as e:
                logger.error(f"💥 {test_name} CRASHED: {e}")
                results.append((test_name, False))
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("SESSION RESUME TEST SUMMARY")
        logger.info(f"{'='*60}")
        
        passed = 0
        failed = 0
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
            if success:
                passed += 1
            else:
                failed += 1
        
        logger.info(f"\nTotal: {len(results)} tests")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        
        if failed == 0:
            logger.info("\n🎉 ALL SESSION RESUME TESTS PASSED!")
            logger.info("\nValidated Functionality:")
            logger.info("- ✅ Basic session resume with event replay")
            logger.info("- ✅ Multiple reconnections consistency")
            logger.info("- ✅ Concurrent session resume")
            logger.info("- ✅ Workflow state preservation during resume")
            logger.info("- ✅ Chronological message ordering")
            return True
        else:
            logger.error(f"\n💥 {failed} SESSION RESUME TESTS FAILED!")
            return False


async def main():
    """Main test runner"""
    test_suite = SessionResumeTest()
    
    try:
        success = await test_suite.run_all_tests()
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        await test_suite.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)