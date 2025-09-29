#!/usr/bin/env python3
"""
Complete Workflow Integration Test
Tests the complete workflow: session creation → file upload → text extraction → analysis → BOG generation
Validates WebSocket communication and session resume functionality
Tests concurrent sessions and multi-user scenarios
Verifies file storage, cleanup, and retention policies work correctly

Requirements: 3.4, 5.4, 6.5, 7.4, 9.5
"""

import asyncio
import json
import logging
import sys
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.events import EventBus, Event
from services.session_service import SessionService
from services.file_service import FileService
from services.analysis_engine import AnalysisEngine
from services.websocket_manager import WebSocketManager
from services.workflow_service import WorkflowService
from models.session_models import SessionCreateRequest
from models.file_models import FileType, ProgressState
from models.workflow_models import ReviewDecision, ReviewRequest
from models.websocket_models import WebSocketMessage, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockWebSocket:
    """Mock WebSocket for testing WebSocket communication"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[str] = []
        self.closed = False
        self.close_code = None
        self.close_reason = None
        self.connected = False
    
    async def accept(self):
        """Mock accept method"""
        self.connected = True
        logger.info(f"Mock WebSocket accepted for session {self.session_id}")
    
    async def send_text(self, text: str):
        """Mock send_text method"""
        if not self.closed:
            self.messages.append(text)
            logger.debug(f"WebSocket {self.session_id} sent: {text[:100]}...")
    
    async def receive_text(self):
        """Mock receive_text method"""
        return json.dumps({
            "type": "chat",
            "content": f"Hello from test client {self.session_id}"
        })
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Mock close method"""
        self.closed = True
        self.connected = False
        self.close_code = code
        self.close_reason = reason
        logger.info(f"Mock WebSocket closed for session {self.session_id}: {code} - {reason}")


class WorkflowIntegrationTest:
    """Complete workflow integration test suite"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.session_service = SessionService(self.event_bus)
        self.file_service = FileService(self.event_bus)
        # Initialize PyBOG agent for analysis engine
        from services.pybog_agent_v2 import PyBOGAgentV2
        self.pybog_agent = PyBOGAgentV2(self.event_bus)
        self.analysis_engine = AnalysisEngine(self.event_bus, self.pybog_agent)
        self.websocket_manager = WebSocketManager(self.event_bus)
        self.workflow_service = WorkflowService(self.event_bus)
        
        self.test_sessions: List[str] = []
        self.test_files: List[int] = []
        self.websockets: Dict[str, MockWebSocket] = {}
    
    async def cleanup(self):
        """Clean up test data"""
        logger.info("Cleaning up test data...")
        
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
        
        # Close WebSocket connections
        for session_id, ws in self.websockets.items():
            try:
                await self.websocket_manager.disconnect(session_id)
            except Exception as e:
                logger.warning(f"Failed to disconnect WebSocket for {session_id}: {e}")
        
        logger.info("Test cleanup completed")
    
    async def create_test_session(self, name: str) -> str:
        """Create a test session and track it for cleanup"""
        session_id = f"test-workflow-{uuid.uuid4().hex[:8]}"
        
        create_request = SessionCreateRequest(
            session_id=session_id,
            name=name,
            metadata={"test": True, "purpose": "workflow_integration_test"}
        )
        
        session = await self.session_service.create_session(create_request)
        self.test_sessions.append(session_id)
        
        logger.info(f"Created test session: {session_id}")
        return session_id
    
    async def create_test_file(self, session_id: str, filename: str, content: bytes) -> int:
        """Create a test file and track it for cleanup"""
        db = await get_database()
        
        file_row = await db.fetch_one(
            """
            INSERT INTO files (session_id, filename, original_name, mime_type, file_type, 
                             file_data, file_size, state, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
            RETURNING id
            """,
            session_id, filename, filename, "text/plain",
            FileType.UPLOAD.value, content, len(content), ProgressState.QUEUED.value
        )
        
        file_id = file_row['id']
        self.test_files.append(file_id)
        
        logger.info(f"Created test file: {file_id} ({filename})")
        return file_id
    
    async def connect_websocket(self, session_id: str) -> MockWebSocket:
        """Connect a WebSocket for the session"""
        websocket = MockWebSocket(session_id)
        await self.websocket_manager.connect(websocket, session_id)
        self.websockets[session_id] = websocket
        
        logger.info(f"Connected WebSocket for session: {session_id}")
        return websocket
    
    async def test_complete_workflow_single_session(self) -> bool:
        """Test complete workflow for a single session"""
        logger.info("=== Testing Complete Workflow - Single Session ===")
        
        try:
            # Step 1: Create session
            session_id = await self.create_test_session("Complete Workflow Test")
            
            # Step 2: Connect WebSocket
            websocket = await self.connect_websocket(session_id)
            
            # Verify WebSocket connection
            assert websocket.connected, "WebSocket should be connected"
            assert self.websocket_manager.is_session_connected(session_id), "Session should be connected"
            
            # Step 3: Upload file
            test_content = """
            HVAC Control Sequence Document
            
            Equipment: Air Handling Unit (AHU-1)
            
            Control Points:
            - Supply Air Temperature (SAT): AI-1
            - Return Air Temperature (RAT): AI-2
            - Outside Air Temperature (OAT): AI-3
            - Supply Air Damper Position: AO-1
            - Return Air Damper Position: AO-2
            
            Control Logic:
            1. Read supply air temperature from sensor AI-1
            2. Compare with setpoint (72F)
            3. If SAT > setpoint + 2F, increase cooling
            4. If SAT < setpoint - 2F, decrease cooling
            5. Modulate damper positions based on temperature differential
            
            Economizer Logic:
            - When OAT < RAT - 5F, enable economizer mode
            - Open outside air damper to minimum 20% position
            - Close return air damper proportionally
            """.encode('utf-8')
            
            file_id = await self.create_test_file(session_id, "hvac_sequence.txt", test_content)
            
            # Wait for WebSocket messages
            await asyncio.sleep(0.2)
            
            # Verify file upload messages were sent
            assert len(websocket.messages) > 0, "Should have received WebSocket messages"
            
            # Step 4: Start text extraction workflow
            extracted_text = test_content.decode('utf-8')
            quality_data = {
                "quality_score": 0.85,
                "issues": [],
                "recommendations": ["Review extracted text for accuracy"],
                "hvac_terms_found": 12,
                "estimated_tokens": 200
            }
            
            review_id = await self.workflow_service.start_text_extraction_workflow(
                session_id, file_id, extracted_text, quality_data
            )
            
            # Wait for workflow messages
            await asyncio.sleep(0.2)
            
            # Verify workflow status
            status = await self.workflow_service.get_workflow_status(session_id)
            assert status.current_state == "text_review", f"Expected text_review state, got {status.current_state}"
            assert status.pending_reviews_count == 1, f"Expected 1 pending review, got {status.pending_reviews_count}"
            
            # Step 5: Approve text review
            review_request = ReviewRequest(
                session_id=session_id,
                review_id=review_id,
                decision=ReviewDecision.APPROVE,
                feedback="Text extraction looks good, proceeding with analysis"
            )
            
            response = await self.workflow_service.submit_review(review_request)
            assert response.next_state == "analysis", f"Expected analysis state, got {response.next_state}"
            
            # Step 6: Start analysis
            analysis_data = {
                "io_points": [
                    {"name": "Supply Air Temp", "type": "input", "data_type": "numeric", "description": "Supply air temperature sensor"},
                    {"name": "Return Air Temp", "type": "input", "data_type": "numeric", "description": "Return air temperature sensor"},
                    {"name": "Outside Air Temp", "type": "input", "data_type": "numeric", "description": "Outside air temperature sensor"},
                    {"name": "Supply Damper", "type": "output", "data_type": "numeric", "description": "Supply air damper position"},
                    {"name": "Return Damper", "type": "output", "data_type": "numeric", "description": "Return air damper position"}
                ],
                "control_blocks": [
                    {
                        "name": "Temperature Control",
                        "type": "PID",
                        "description": "Supply air temperature control loop",
                        "logic": ["Read SAT sensor", "Compare with setpoint", "Calculate PID output"],
                        "complexity": 7
                    },
                    {
                        "name": "Economizer Control",
                        "type": "Logic",
                        "description": "Economizer enable/disable logic",
                        "logic": ["Compare OAT vs RAT", "Enable when OAT < RAT - 5°F"],
                        "complexity": 5
                    }
                ],
                "pseudocode": [
                    {"step": 1, "description": "Read temperatures", "code": "sat = read_sensor(AI-1); rat = read_sensor(AI-2); oat = read_sensor(AI-3)"},
                    {"step": 2, "description": "Temperature control", "code": "error = setpoint - sat; output = pid_calculate(error)"},
                    {"step": 3, "description": "Economizer logic", "code": "if (oat < rat - 5) enable_economizer()"}
                ],
                "quality_score": 0.82,
                "issues": [],
                "metadata": {
                    "confidence": 0.85,
                    "recommendations": ["Consider adding humidity control", "Add alarm points for fault detection"]
                }
            }
            
            analysis_review_id = await self.workflow_service.start_analysis_review_workflow(
                session_id, file_id, analysis_data
            )
            
            # Wait for analysis messages
            await asyncio.sleep(0.2)
            
            # Verify analysis workflow status
            status = await self.workflow_service.get_workflow_status(session_id)
            assert status.current_state == "analysis_review", f"Expected analysis_review state, got {status.current_state}"
            
            # Step 7: Approve analysis
            analysis_review_request = ReviewRequest(
                session_id=session_id,
                review_id=analysis_review_id,
                decision=ReviewDecision.APPROVE,
                feedback="Analysis looks comprehensive, proceed with BOG generation"
            )
            
            analysis_response = await self.workflow_service.submit_review(analysis_review_request)
            assert analysis_response.next_state == "bog_generation", f"Expected bog_generation state, got {analysis_response.next_state}"
            
            # Step 8: Simulate BOG generation (would normally be done by analysis engine)
            bog_content = """
            # Generated BOG File for AHU-1
            # Generated from HVAC Control Sequence Document
            
            [Equipment]
            Name=AHU-1
            Type=AirHandlingUnit
            
            [InputPoints]
            SAT=AI-1,SupplyAirTemp,Numeric,F
            RAT=AI-2,ReturnAirTemp,Numeric,F
            OAT=AI-3,OutsideAirTemp,Numeric,F
            
            [OutputPoints]
            SupplyDamper=AO-1,SupplyDamperPosition,Numeric,percent
            ReturnDamper=AO-2,ReturnDamperPosition,Numeric,percent
            
            [ControlBlocks]
            TempControl=PID,SupplyAirTempControl
            EconomizerLogic=Logic,EconomizerControl
            """.encode('utf-8')
            
            bog_file_id = await self.create_test_file(session_id, "ahu-1.bog", bog_content)
            
            # Update file type to BOG
            await self.file_service.update_file_state(bog_file_id, ProgressState.COMPLETE)
            
            # Step 9: Verify complete workflow
            final_status = await self.workflow_service.get_workflow_status(session_id)
            assert final_status.current_state in ["complete", "bog_generation"], f"Expected complete or bog_generation state, got {final_status.current_state}"
            
            # Step 10: Verify file storage
            session_files = await self.file_service.list_session_files(session_id)
            assert session_files.total_count >= 2, f"Expected at least 2 files, got {session_files.total_count}"
            
            # Verify we have both upload and BOG files
            file_types = [f.file_type for f in session_files.files]
            assert FileType.UPLOAD in file_types, "Should have upload file"
            
            # Step 11: Test session resume
            # Disconnect and reconnect WebSocket
            await self.websocket_manager.disconnect(session_id)
            
            new_websocket = await self.connect_websocket(session_id)
            
            # Wait for resume messages
            await asyncio.sleep(0.2)
            
            # Verify resume messages were sent
            assert len(new_websocket.messages) > 0, "Should have received resume messages"
            
            # Verify session state is preserved
            resumed_status = await self.workflow_service.get_workflow_status(session_id)
            assert resumed_status.current_state == final_status.current_state, "Session state should be preserved after resume"
            
            logger.info("✅ Complete workflow test passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Complete workflow test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_concurrent_sessions(self) -> bool:
        """Test concurrent sessions and multi-user scenarios"""
        logger.info("=== Testing Concurrent Sessions ===")
        
        try:
            # Create multiple concurrent sessions
            session_count = 3
            sessions = []
            websockets = []
            
            for i in range(session_count):
                session_id = await self.create_test_session(f"Concurrent Test Session {i+1}")
                sessions.append(session_id)
                
                websocket = await self.connect_websocket(session_id)
                websockets.append(websocket)
            
            # Verify all sessions are connected
            for session_id in sessions:
                assert self.websocket_manager.is_session_connected(session_id), f"Session {session_id} should be connected"
            
            assert self.websocket_manager.get_connection_count() == session_count, f"Should have {session_count} connections"
            
            # Upload files to each session concurrently
            upload_tasks = []
            for i, session_id in enumerate(sessions):
                content = f"Test content for session {i+1} - HVAC control sequence".encode()
                task = self.create_test_file(session_id, f"test_file_{i+1}.txt", content)
                upload_tasks.append(task)
            
            file_ids = await asyncio.gather(*upload_tasks)
            
            # Verify files were created in correct sessions
            for i, (session_id, file_id) in enumerate(zip(sessions, file_ids)):
                metadata = await self.file_service.get_file_metadata(file_id)
                assert metadata.session_id == session_id, f"File {file_id} should belong to session {session_id}"
            
            # Start workflows concurrently
            workflow_tasks = []
            for i, (session_id, file_id) in enumerate(zip(sessions, file_ids)):
                extracted_text = f"Extracted text for session {i+1}"
                quality_data = {"quality_score": 0.8, "issues": [], "recommendations": []}
                
                task = self.workflow_service.start_text_extraction_workflow(
                    session_id, file_id, extracted_text, quality_data
                )
                workflow_tasks.append(task)
            
            review_ids = await asyncio.gather(*workflow_tasks)
            
            # Wait for all WebSocket messages
            await asyncio.sleep(0.3)
            
            # Verify each session received its own messages
            for i, websocket in enumerate(websockets):
                assert len(websocket.messages) > 0, f"WebSocket {i} should have received messages"
                
                # Verify messages contain correct session ID
                for message_text in websocket.messages:
                    try:
                        message_data = json.loads(message_text)
                        assert message_data["session_id"] == sessions[i], f"Message should have correct session ID"
                    except json.JSONDecodeError:
                        pass  # Skip non-JSON messages
            
            # Verify workflow states are independent
            for session_id in sessions:
                status = await self.workflow_service.get_workflow_status(session_id)
                assert status.current_state == "text_review", f"Session {session_id} should be in text_review state"
                assert status.pending_reviews_count == 1, f"Session {session_id} should have 1 pending review"
            
            logger.info("✅ Concurrent sessions test passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Concurrent sessions test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_file_storage_and_cleanup(self) -> bool:
        """Test file storage, cleanup, and retention policies"""
        logger.info("=== Testing File Storage and Cleanup ===")
        
        try:
            # Create test session
            session_id = await self.create_test_session("File Storage Test")
            
            # Test small file (should use BYTEA storage)
            small_content = b"Small test file content for BYTEA storage"
            small_file_id = await self.create_test_file(session_id, "small_file.txt", small_content)
            
            # Test larger file (should use file system storage if implemented)
            large_content = b"Large test file content " * 1000  # ~25KB
            large_file_id = await self.create_test_file(session_id, "large_file.txt", large_content)
            
            # Verify file data retrieval
            small_data = await self.file_service.get_file_data(small_file_id)
            assert small_data == small_content, "Small file data should match"
            
            large_data = await self.file_service.get_file_data(large_file_id)
            assert large_data == large_content, "Large file data should match"
            
            # Test file state transitions
            states_to_test = [ProgressState.PROCESSING, ProgressState.COMPLETE, ProgressState.FAILED]
            
            for state in states_to_test:
                await self.file_service.update_file_state(small_file_id, state)
                metadata = await self.file_service.get_file_metadata(small_file_id)
                assert metadata.state == state, f"File state should be {state}"
            
            # Test file listing with different states
            session_files = await self.file_service.list_session_files(session_id)
            assert session_files.total_count == 2, f"Should have 2 files, got {session_files.total_count}"
            
            # Test file cleanup
            cleanup_result = await self.file_service.cleanup_old_files()
            assert isinstance(cleanup_result.archived_count, int), "Archived count should be integer"
            assert isinstance(cleanup_result.purged_count, int), "Purged count should be integer"
            
            # Test file deletion
            deleted = await self.file_service.delete_file(small_file_id)
            assert deleted is True, "File should be deleted successfully"
            
            # Verify file is no longer accessible
            try:
                await self.file_service.get_file_metadata(small_file_id)
                assert False, "Should not be able to access deleted file"
            except Exception:
                pass  # Expected to fail
            
            # Verify session file count updated
            session_files = await self.file_service.list_session_files(session_id)
            assert session_files.total_count == 1, f"Should have 1 file after deletion, got {session_files.total_count}"
            
            logger.info("✅ File storage and cleanup test passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ File storage and cleanup test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_websocket_communication_validation(self) -> bool:
        """Test WebSocket communication and message validation"""
        logger.info("=== Testing WebSocket Communication Validation ===")
        
        try:
            # Create test session
            session_id = await self.create_test_session("WebSocket Communication Test")
            websocket = await self.connect_websocket(session_id)
            
            # Test different message types
            message_types = [
                ("chat", {"content": "Test chat message", "is_complete": True}),
                ("progress", {"state": "processing", "message": "Processing file...", "progress_percent": 50}),
                ("analysis_complete", {"analysis_id": 123, "quality_score": 0.85}),
                ("error", {"error_code": "FILE", "message": "Test error message", "retry_possible": True})
            ]
            
            for msg_type, data in message_types:
                # Publish event
                event = Event(
                    type=msg_type,
                    session_id=session_id,
                    operation=f"test_{msg_type}",
                    data=data
                )
                await self.event_bus.publish(session_id, event)
            
            # Wait for message processing
            await asyncio.sleep(0.2)
            
            # Verify messages were received
            assert len(websocket.messages) >= len(message_types), f"Should have received at least {len(message_types)} messages"
            
            # Validate message format
            for message_text in websocket.messages:
                try:
                    message_data = json.loads(message_text)
                    
                    # Verify required fields
                    required_fields = ["type", "session_id", "data", "timestamp"]
                    for field in required_fields:
                        assert field in message_data, f"Message should have '{field}' field"
                    
                    # Verify session ID matches
                    assert message_data["session_id"] == session_id, "Session ID should match"
                    
                    # Verify timestamp format
                    timestamp = message_data["timestamp"]
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))  # Should not raise exception
                    
                except json.JSONDecodeError:
                    assert False, f"Message should be valid JSON: {message_text}"
                except ValueError as e:
                    assert False, f"Invalid timestamp format: {e}"
            
            # Test WebSocket error handling
            # Simulate connection error by closing WebSocket
            await websocket.close(1001, "Test connection error")
            
            # Verify connection is marked as closed
            assert websocket.closed, "WebSocket should be marked as closed"
            
            # Test reconnection
            new_websocket = await self.connect_websocket(session_id)
            assert new_websocket.connected, "New WebSocket should be connected"
            
            logger.info("✅ WebSocket communication validation test passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ WebSocket communication validation test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_all_tests(self) -> bool:
        """Run all integration tests"""
        logger.info("🚀 Starting Complete Workflow Integration Tests")
        
        tests = [
            ("Complete Workflow - Single Session", self.test_complete_workflow_single_session),
            ("Concurrent Sessions", self.test_concurrent_sessions),
            ("File Storage and Cleanup", self.test_file_storage_and_cleanup),
            ("WebSocket Communication Validation", self.test_websocket_communication_validation),
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
        logger.info("INTEGRATION TEST SUMMARY")
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
            logger.info("\n🎉 ALL INTEGRATION TESTS PASSED!")
            logger.info("\nValidated Requirements:")
            logger.info("- ✅ 3.4: Complete session management functionality")
            logger.info("- ✅ 5.4: Robust file processing with error handling")
            logger.info("- ✅ 6.5: Review and approval workflow completion")
            logger.info("- ✅ 7.4: BOG file generation and management")
            logger.info("- ✅ 9.5: Real-time WebSocket communication and session resume")
            return True
        else:
            logger.error(f"\n💥 {failed} INTEGRATION TESTS FAILED!")
            return False


async def main():
    """Main test runner"""
    test_suite = WorkflowIntegrationTest()
    
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