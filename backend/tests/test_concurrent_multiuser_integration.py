#!/usr/bin/env python3
"""
Concurrent Multi-User Integration Test
Tests concurrent sessions, multi-user scenarios, and system scalability
Validates isolation between users and proper resource management

Requirements: 3.4, 9.5 - Session management and real-time communication
"""

import asyncio
import json
import logging
import sys
import uuid
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.events import EventBus, Event
from services.websocket_manager import WebSocketManager
from services.session_service import SessionService
from services.file_service import FileService
from services.workflow_service import WorkflowService
from models.session_models import SessionCreateRequest
from models.file_models import FileType, ProgressState
from models.workflow_models import ReviewDecision, ReviewRequest

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockUser:
    """Represents a mock user with multiple sessions"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sessions: List[str] = []
        self.websockets: Dict[str, 'MockWebSocket'] = {}
        self.activity_count = 0
    
    def add_session(self, session_id: str):
        """Add a session to this user"""
        self.sessions.append(session_id)
    
    def add_websocket(self, session_id: str, websocket: 'MockWebSocket'):
        """Add a WebSocket connection for a session"""
        self.websockets[session_id] = websocket
    
    def get_total_messages(self) -> int:
        """Get total messages received across all sessions"""
        return sum(len(ws.messages) for ws in self.websockets.values())


class MockWebSocket:
    """Mock WebSocket for multi-user testing"""
    
    def __init__(self, session_id: str, user_id: str, connection_id: str = None):
        self.session_id = session_id
        self.user_id = user_id
        self.connection_id = connection_id or f"conn-{uuid.uuid4().hex[:8]}"
        self.messages: List[str] = []
        self.closed = False
        self.connected = False
        self.message_types: Dict[str, int] = {}
    
    async def accept(self):
        """Mock accept method"""
        self.connected = True
        logger.debug(f"WebSocket {self.connection_id} accepted for user {self.user_id}, session {self.session_id}")
    
    async def send_text(self, text: str):
        """Mock send_text method"""
        if not self.closed:
            self.messages.append(text)
            
            # Track message types for analysis
            try:
                message_data = json.loads(text)
                msg_type = message_data.get("type", "unknown")
                self.message_types[msg_type] = self.message_types.get(msg_type, 0) + 1
            except json.JSONDecodeError:
                pass
            
            logger.debug(f"WebSocket {self.connection_id} sent message (total: {len(self.messages)})")
    
    async def receive_text(self):
        """Mock receive_text method"""
        return json.dumps({
            "type": "chat",
            "content": f"Hello from user {self.user_id}"
        })
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Mock close method"""
        self.closed = True
        self.connected = False
        logger.debug(f"WebSocket {self.connection_id} closed for user {self.user_id}")


class ConcurrentMultiUserTest:
    """Concurrent multi-user integration test suite"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.websocket_manager = WebSocketManager(self.event_bus)
        self.session_service = SessionService(self.event_bus)
        self.file_service = FileService(self.event_bus)
        self.workflow_service = WorkflowService(self.event_bus)
        
        self.users: Dict[str, MockUser] = {}
        self.test_sessions: List[str] = []
        self.test_files: List[int] = []
    
    async def cleanup(self):
        """Clean up test data"""
        logger.info("Cleaning up multi-user test data...")
        
        # Disconnect all WebSockets
        for user in self.users.values():
            for session_id in user.sessions:
                try:
                    await self.websocket_manager.disconnect(session_id)
                except Exception as e:
                    logger.warning(f"Failed to disconnect session {session_id}: {e}")
        
        # Clean up files
        for file_id in self.test_files:
            try:
                await self.file_service.delete_file(file_id)
            except Exception as e:
                logger.warning(f"Failed to delete test file {file_id}: {e}")
        
        # Clean up sessions
        for session_id in self.test_sessions:
            try:
                await self.session_service.delete_session(session_id)
            except Exception as e:
                logger.warning(f"Failed to delete test session {session_id}: {e}")
        
        logger.info("Multi-user test cleanup completed")
    
    async def create_user(self, user_id: str) -> MockUser:
        """Create a mock user"""
        user = MockUser(user_id)
        self.users[user_id] = user
        logger.info(f"Created user: {user_id}")
        return user
    
    async def create_session_for_user(self, user: MockUser, session_name: str) -> str:
        """Create a session for a user"""
        session_id = f"test-multiuser-{user.user_id}-{uuid.uuid4().hex[:8]}"
        
        create_request = SessionCreateRequest(
            session_id=session_id,
            name=f"{user.user_id}: {session_name}",
            metadata={"test": True, "user_id": user.user_id, "purpose": "multiuser_test"}
        )
        
        session = await self.session_service.create_session(create_request)
        user.add_session(session_id)
        self.test_sessions.append(session_id)
        
        logger.info(f"Created session {session_id} for user {user.user_id}")
        return session_id
    
    async def connect_websocket_for_session(self, user: MockUser, session_id: str) -> MockWebSocket:
        """Connect a WebSocket for a user's session"""
        websocket = MockWebSocket(session_id, user.user_id)
        await self.websocket_manager.connect(websocket, session_id)
        user.add_websocket(session_id, websocket)
        
        logger.info(f"Connected WebSocket for user {user.user_id}, session {session_id}")
        return websocket
    
    async def simulate_user_activity(self, user: MockUser, session_id: str, activity_count: int = 5):
        """Simulate user activity in a session"""
        activities = [
            ("chat", {"content": f"User {user.user_id} message", "is_complete": True}),
            ("progress", {"state": "processing", "message": f"Processing for {user.user_id}", "progress_percent": 30}),
            ("file_uploaded", {"file_id": random.randint(100, 999), "filename": f"user_{user.user_id}_file.txt"}),
            ("analysis_complete", {"analysis_id": random.randint(1000, 9999), "quality_score": random.uniform(0.7, 0.95)}),
            ("error", {"error_code": "TEMP", "message": f"Temporary error for {user.user_id}", "retry_possible": True})
        ]
        
        for i in range(activity_count):
            activity_type, data = random.choice(activities)
            
            event = Event(
                type=activity_type,
                session_id=session_id,
                operation=f"user_activity_{user.user_id}_{i}",
                data=data,
                metadata={"user_id": user.user_id, "activity_sequence": i}
            )
            
            await self.event_bus.publish(session_id, event)
            user.activity_count += 1
            
            # Random delay to simulate realistic timing
            await asyncio.sleep(random.uniform(0.01, 0.05))
        
        logger.info(f"Simulated {activity_count} activities for user {user.user_id} in session {session_id}")
    
    async def test_concurrent_users_single_session_each(self) -> bool:
        """Test multiple users with one session each"""
        logger.info("=== Testing Concurrent Users - Single Session Each ===")
        
        try:
            user_count = 5
            users = []
            
            # Create users and sessions
            for i in range(user_count):
                user_id = f"user_{i+1:02d}"
                user = await self.create_user(user_id)
                users.append(user)
                
                session_id = await self.create_session_for_user(user, f"Single Session Test")
                await self.connect_websocket_for_session(user, session_id)
            
            # Verify all connections
            total_connections = self.websocket_manager.get_connection_count()
            assert total_connections == user_count, f"Expected {user_count} connections, got {total_connections}"
            
            # Simulate concurrent activity
            activity_tasks = []
            for user in users:
                for session_id in user.sessions:
                    task = self.simulate_user_activity(user, session_id, 8)
                    activity_tasks.append(task)
            
            await asyncio.gather(*activity_tasks)
            
            # Wait for message processing
            await asyncio.sleep(0.3)
            
            # Verify message isolation (each user should only receive their own messages)
            for user in users:
                total_messages = user.get_total_messages()
                assert total_messages > 0, f"User {user.user_id} should have received messages"
                
                # Check that messages contain correct session IDs
                for session_id, websocket in user.websockets.items():
                    for message_text in websocket.messages[:5]:  # Check first 5 messages
                        try:
                            message_data = json.loads(message_text)
                            msg_session_id = message_data.get("session_id")
                            assert msg_session_id == session_id, f"Message session ID should match: expected {session_id}, got {msg_session_id}"
                        except json.JSONDecodeError:
                            pass
            
            # Verify session isolation
            session_stats = await self.session_service.get_session_stats()
            assert session_stats.total_sessions >= user_count, f"Should have at least {user_count} sessions"
            
            logger.info(f"✅ Concurrent users single session test passed!")
            logger.info(f"   Users: {user_count}")
            logger.info(f"   Total connections: {total_connections}")
            logger.info(f"   Total sessions: {session_stats.total_sessions}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Concurrent users single session test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_single_user_multiple_sessions(self) -> bool:
        """Test single user with multiple sessions"""
        logger.info("=== Testing Single User - Multiple Sessions ===")
        
        try:
            user = await self.create_user("multi_session_user")
            session_count = 4
            
            # Create multiple sessions for the user
            for i in range(session_count):
                session_id = await self.create_session_for_user(user, f"Multi Session {i+1}")
                await self.connect_websocket_for_session(user, session_id)
            
            # Verify connections
            assert len(user.sessions) == session_count, f"User should have {session_count} sessions"
            assert len(user.websockets) == session_count, f"User should have {session_count} WebSocket connections"
            
            # Simulate activity in all sessions concurrently
            activity_tasks = []
            for session_id in user.sessions:
                task = self.simulate_user_activity(user, session_id, 6)
                activity_tasks.append(task)
            
            await asyncio.gather(*activity_tasks)
            
            # Wait for message processing
            await asyncio.sleep(0.3)
            
            # Verify each session received its own messages
            for session_id, websocket in user.websockets.items():
                assert len(websocket.messages) > 0, f"Session {session_id} should have received messages"
                
                # Verify message session ID isolation
                for message_text in websocket.messages[:3]:
                    try:
                        message_data = json.loads(message_text)
                        msg_session_id = message_data.get("session_id")
                        assert msg_session_id == session_id, f"Message should belong to correct session"
                    except json.JSONDecodeError:
                        pass
            
            # Test session switching (disconnect from one, connect to another)
            first_session = user.sessions[0]
            await self.websocket_manager.disconnect(first_session)
            
            # Reconnect to the same session
            new_websocket = await self.connect_websocket_for_session(user, first_session)
            
            # Wait for resume
            await asyncio.sleep(0.2)
            
            # Verify resume worked
            assert len(new_websocket.messages) > 0, "Reconnected session should have resume messages"
            
            logger.info(f"✅ Single user multiple sessions test passed!")
            logger.info(f"   Sessions per user: {session_count}")
            logger.info(f"   Total messages: {user.get_total_messages()}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Single user multiple sessions test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_high_concurrency_stress(self) -> bool:
        """Test high concurrency stress scenario"""
        logger.info("=== Testing High Concurrency Stress ===")
        
        try:
            user_count = 10
            sessions_per_user = 2
            total_sessions = user_count * sessions_per_user
            
            # Create users and sessions
            setup_tasks = []
            users = []
            
            for i in range(user_count):
                user_id = f"stress_user_{i+1:02d}"
                user = await self.create_user(user_id)
                users.append(user)
                
                for j in range(sessions_per_user):
                    session_task = self.create_session_for_user(user, f"Stress Session {j+1}")
                    setup_tasks.append(session_task)
            
            # Create all sessions concurrently
            session_ids = await asyncio.gather(*setup_tasks)
            
            # Connect WebSockets concurrently
            connection_tasks = []
            for user in users:
                for session_id in user.sessions:
                    task = self.connect_websocket_for_session(user, session_id)
                    connection_tasks.append(task)
            
            await asyncio.gather(*connection_tasks)
            
            # Verify all connections
            total_connections = self.websocket_manager.get_connection_count()
            assert total_connections == total_sessions, f"Expected {total_sessions} connections, got {total_connections}"
            
            # Generate high-volume concurrent activity
            activity_tasks = []
            for user in users:
                for session_id in user.sessions:
                    # More activities for stress test
                    task = self.simulate_user_activity(user, session_id, 12)
                    activity_tasks.append(task)
            
            # Execute all activities concurrently
            start_time = datetime.now()
            await asyncio.gather(*activity_tasks)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            
            # Wait for message processing
            await asyncio.sleep(0.5)
            
            # Verify system handled the load
            total_messages = sum(user.get_total_messages() for user in users)
            total_activities = sum(user.activity_count for user in users)
            
            assert total_messages > 0, "Should have processed messages"
            assert total_activities > 0, "Should have processed activities"
            
            # Verify message distribution
            for user in users:
                user_messages = user.get_total_messages()
                assert user_messages > 0, f"User {user.user_id} should have received messages"
            
            # Test random disconnections and reconnections
            disconnect_count = min(5, len(users))
            disconnect_users = random.sample(users, disconnect_count)
            
            for user in disconnect_users:
                session_to_disconnect = random.choice(user.sessions)
                await self.websocket_manager.disconnect(session_to_disconnect)
            
            # Reconnect
            reconnect_tasks = []
            for user in disconnect_users:
                for session_id in user.sessions:
                    if not self.websocket_manager.is_session_connected(session_id):
                        task = self.connect_websocket_for_session(user, session_id)
                        reconnect_tasks.append(task)
            
            if reconnect_tasks:
                await asyncio.gather(*reconnect_tasks)
            
            logger.info(f"✅ High concurrency stress test passed!")
            logger.info(f"   Users: {user_count}")
            logger.info(f"   Sessions per user: {sessions_per_user}")
            logger.info(f"   Total sessions: {total_sessions}")
            logger.info(f"   Total messages: {total_messages}")
            logger.info(f"   Total activities: {total_activities}")
            logger.info(f"   Processing time: {processing_time:.2f}s")
            logger.info(f"   Disconnected/reconnected: {disconnect_count} users")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ High concurrency stress test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_message_isolation_verification(self) -> bool:
        """Test strict message isolation between users"""
        logger.info("=== Testing Message Isolation Verification ===")
        
        try:
            # Create two users with distinct activity patterns
            user_a = await self.create_user("isolation_user_a")
            user_b = await self.create_user("isolation_user_b")
            
            session_a = await self.create_session_for_user(user_a, "Isolation Test A")
            session_b = await self.create_session_for_user(user_b, "Isolation Test B")
            
            ws_a = await self.connect_websocket_for_session(user_a, session_a)
            ws_b = await self.connect_websocket_for_session(user_b, session_b)
            
            # Generate distinct events for each user
            event_a = Event(
                type="chat",
                session_id=session_a,
                operation="user_a_unique_message",
                data={"content": "UNIQUE_MESSAGE_FOR_USER_A", "user_marker": "USER_A", "is_complete": True}
            )
            
            event_b = Event(
                type="chat",
                session_id=session_b,
                operation="user_b_unique_message",
                data={"content": "UNIQUE_MESSAGE_FOR_USER_B", "user_marker": "USER_B", "is_complete": True}
            )
            
            # Publish events
            await self.event_bus.publish(session_a, event_a)
            await self.event_bus.publish(session_b, event_b)
            
            # Wait for processing
            await asyncio.sleep(0.2)
            
            # Verify isolation - User A should not receive User B's messages and vice versa
            user_a_messages = [json.loads(msg) for msg in ws_a.messages if msg.strip()]
            user_b_messages = [json.loads(msg) for msg in ws_b.messages if msg.strip()]
            
            # Check User A messages
            user_a_found_own = False
            user_a_found_other = False
            
            for msg in user_a_messages:
                if msg.get("session_id") == session_a:
                    data = msg.get("data", {})
                    if data.get("user_marker") == "USER_A":
                        user_a_found_own = True
                    elif data.get("user_marker") == "USER_B":
                        user_a_found_other = True
            
            # Check User B messages
            user_b_found_own = False
            user_b_found_other = False
            
            for msg in user_b_messages:
                if msg.get("session_id") == session_b:
                    data = msg.get("data", {})
                    if data.get("user_marker") == "USER_B":
                        user_b_found_own = True
                    elif data.get("user_marker") == "USER_A":
                        user_b_found_other = True
            
            # Verify isolation
            assert user_a_found_own, "User A should have received their own message"
            assert not user_a_found_other, "User A should NOT have received User B's message"
            assert user_b_found_own, "User B should have received their own message"
            assert not user_b_found_other, "User B should NOT have received User A's message"
            
            # Verify session ID isolation
            for msg in user_a_messages:
                session_id = msg.get("session_id")
                assert session_id == session_a, f"User A should only receive messages for session {session_a}, got {session_id}"
            
            for msg in user_b_messages:
                session_id = msg.get("session_id")
                assert session_id == session_b, f"User B should only receive messages for session {session_b}, got {session_id}"
            
            logger.info(f"✅ Message isolation verification test passed!")
            logger.info(f"   User A messages: {len(user_a_messages)}")
            logger.info(f"   User B messages: {len(user_b_messages)}")
            logger.info(f"   Isolation verified: ✓")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Message isolation verification test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all concurrent multi-user tests"""
        logger.info("🚀 Starting Concurrent Multi-User Integration Tests")
        
        tests = [
            ("Concurrent Users - Single Session Each", self.test_concurrent_users_single_session_each),
            ("Single User - Multiple Sessions", self.test_single_user_multiple_sessions),
            ("High Concurrency Stress", self.test_high_concurrency_stress),
            ("Message Isolation Verification", self.test_message_isolation_verification),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*70}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*70}")
            
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
        logger.info(f"\n{'='*70}")
        logger.info("CONCURRENT MULTI-USER TEST SUMMARY")
        logger.info(f"{'='*70}")
        
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
            logger.info("\n🎉 ALL CONCURRENT MULTI-USER TESTS PASSED!")
            logger.info("\nValidated Functionality:")
            logger.info("- ✅ Concurrent user session isolation")
            logger.info("- ✅ Single user multiple session management")
            logger.info("- ✅ High concurrency stress handling")
            logger.info("- ✅ Strict message isolation between users")
            logger.info("- ✅ WebSocket connection management at scale")
            return True
        else:
            logger.error(f"\n💥 {failed} CONCURRENT MULTI-USER TESTS FAILED!")
            return False


async def main():
    """Main test runner"""
    test_suite = ConcurrentMultiUserTest()
    
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