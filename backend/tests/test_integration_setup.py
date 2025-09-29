#!/usr/bin/env python3
"""
Integration Test Setup Verification
Verifies that all required components are available and properly configured
before running the full integration test suite.

This is a prerequisite check for task 13 integration tests.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_imports():
    """Test that all required modules can be imported"""
    logger.info("Testing module imports...")
    
    try:
        # Core modules
        from core.database import get_database
        from core.events import EventBus, Event
        logger.info("✅ Core modules imported successfully")
        
        # Service modules
        from services.session_service import SessionService
        from services.file_service import FileService
        from services.analysis_engine import AnalysisEngine
        from services.websocket_manager import WebSocketManager
        from services.workflow_service import WorkflowService
        logger.info("✅ Service modules imported successfully")
        
        # Model modules
        from models.session_models import SessionCreateRequest
        from models.file_models import FileType, ProgressState
        from models.workflow_models import ReviewDecision, ReviewRequest
        from models.websocket_models import WebSocketMessage, MessageType
        logger.info("✅ Model modules imported successfully")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during import: {e}")
        return False


async def test_database_connection():
    """Test basic database connectivity"""
    logger.info("Testing database connection...")
    
    try:
        from core.database import get_database
        
        db = await get_database()
        
        # Test basic query
        result = await db.fetch_val("SELECT 1")
        assert result == 1, "Basic query failed"
        
        # Test health check
        health = await db.health_check()
        assert health["status"] == "healthy", f"Health check failed: {health}"
        
        logger.info("✅ Database connection successful")
        logger.info(f"   Pool size: {health['pool_stats']['size']}")
        logger.info(f"   Available connections: {health['pool_stats']['freesize']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def test_service_initialization():
    """Test that all services can be initialized"""
    logger.info("Testing service initialization...")
    
    try:
        from core.events import EventBus
        from services.session_service import SessionService
        from services.file_service import FileService
        from services.websocket_manager import WebSocketManager
        from services.workflow_service import WorkflowService
        
        # Initialize event bus
        event_bus = EventBus()
        logger.info("✅ EventBus initialized")
        
        # Initialize services
        session_service = SessionService(event_bus)
        logger.info("✅ SessionService initialized")
        
        file_service = FileService(event_bus)
        logger.info("✅ FileService initialized")
        
        websocket_manager = WebSocketManager(event_bus)
        logger.info("✅ WebSocketManager initialized")
        
        workflow_service = WorkflowService(event_bus)
        logger.info("✅ WorkflowService initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_basic_functionality():
    """Test basic functionality of key components"""
    logger.info("Testing basic functionality...")
    
    try:
        from core.events import EventBus, Event
        from services.session_service import SessionService
        from models.session_models import SessionCreateRequest
        
        # Test event bus
        event_bus = EventBus()
        
        test_event = Event(
            type="test",
            session_id="test-session",
            operation="setup_test",
            data={"message": "Setup test event"}
        )
        
        await event_bus.publish("test-session", test_event)
        logger.info("✅ EventBus publish/subscribe working")
        
        # Test session service
        session_service = SessionService(event_bus)
        
        # Get session stats (should not fail)
        stats = await session_service.get_session_stats()
        assert hasattr(stats, 'total_sessions'), "Session stats should have total_sessions"
        logger.info(f"✅ SessionService basic functionality working (total sessions: {stats.total_sessions})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_integration_test_modules():
    """Test that integration test modules can be imported"""
    logger.info("Testing integration test module imports...")
    
    try:
        # Test integration test imports
        from tests.test_complete_workflow_integration import WorkflowIntegrationTest
        logger.info("✅ WorkflowIntegrationTest imported")
        
        from tests.test_session_resume_integration import SessionResumeTest
        logger.info("✅ SessionResumeTest imported")
        
        from tests.test_concurrent_multiuser_integration import ConcurrentMultiUserTest
        logger.info("✅ ConcurrentMultiUserTest imported")
        
        # Test that test classes can be instantiated
        workflow_test = WorkflowIntegrationTest()
        logger.info("✅ WorkflowIntegrationTest instantiated")
        
        resume_test = SessionResumeTest()
        logger.info("✅ SessionResumeTest instantiated")
        
        multiuser_test = ConcurrentMultiUserTest()
        logger.info("✅ ConcurrentMultiUserTest instantiated")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Integration test module import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Integration test module error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_setup_verification():
    """Run all setup verification tests"""
    logger.info("🔍 STARTING INTEGRATION TEST SETUP VERIFICATION")
    logger.info("="*60)
    
    tests = [
        ("Module Imports", test_imports),
        ("Database Connection", test_database_connection),
        ("Service Initialization", test_service_initialization),
        ("Basic Functionality", test_basic_functionality),
        ("Integration Test Modules", test_integration_test_modules),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running: {test_name} ---")
        
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
    logger.info("SETUP VERIFICATION SUMMARY")
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
        logger.info("\n🎉 SETUP VERIFICATION PASSED!")
        logger.info("✅ System is ready for integration testing")
        logger.info("✅ You can now run the full integration test suite")
        return True
    else:
        logger.error(f"\n💥 {failed} SETUP VERIFICATION(S) FAILED!")
        logger.error("❌ System is not ready for integration testing")
        logger.error("❌ Please fix the issues above before running integration tests")
        return False


async def main():
    """Main entry point"""
    try:
        success = await run_setup_verification()
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Setup verification crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)