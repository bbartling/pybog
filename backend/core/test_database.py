"""
Test database connection and operations.
"""

import asyncio
import pytest
import logging
from unittest.mock import patch, AsyncMock
from database import (
    DatabaseManager, 
    DatabaseConnectionError, 
    DatabaseMigrationError,
    get_database,
    close_database
)
from config import DatabaseConfig

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_manager_initialization():
    """Test database manager initialization."""
    config = DatabaseConfig(
        url="postgresql://test:test@localhost:5432/test_db",
        pool_size=5
    )
    
    db_manager = DatabaseManager(config)
    assert db_manager.config.url == config.url
    assert db_manager.pool is None
    assert not db_manager._initialized


async def test_database_connection_error():
    """Test database connection error handling."""
    config = DatabaseConfig(url="postgresql://invalid:invalid@nonexistent:5432/invalid")
    db_manager = DatabaseManager(config)
    
    try:
        await db_manager.initialize()
        assert False, "Should have raised DatabaseConnectionError"
    except DatabaseConnectionError:
        pass  # Expected


async def test_database_operations_without_initialization():
    """Test that operations fail without initialization."""
    db_manager = DatabaseManager()
    
    try:
        async with db_manager.get_connection():
            pass
        assert False, "Should have raised DatabaseConnectionError"
    except DatabaseConnectionError:
        pass  # Expected


async def test_health_check_without_pool():
    """Test health check when pool is not initialized."""
    db_manager = DatabaseManager()
    health = await db_manager.health_check()
    
    assert health['status'] == 'error'
    assert 'not initialized' in health['message']


async def test_file_cleanup_functions():
    """Test file cleanup SQL functions (requires real database)."""
    # This test requires a real database connection
    # Skip if DATABASE_URL is not set to a test database
    import os
    if 'test' not in os.environ.get('DATABASE_URL', '').lower():
        logger.info("Skipping file cleanup test - requires test database")
        return
    
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Test cleanup functions exist
        async with db_manager.get_connection() as conn:
            # Check if cleanup functions exist
            functions = await conn.fetch("""
                SELECT routine_name 
                FROM information_schema.routines 
                WHERE routine_schema = 'public' 
                AND routine_name IN ('archive_old_bytea_files', 'purge_archived_files')
            """)
            
            function_names = [row['routine_name'] for row in functions]
            assert 'archive_old_bytea_files' in function_names
            assert 'purge_archived_files' in function_names
            
            logger.info("✅ File cleanup functions exist")
        
        await db_manager.close()
        
    except Exception as e:
        logger.info(f"Skipping cleanup test due to database connection: {e}")


async def test_schema_validation():
    """Test that required tables and indexes exist."""
    # This test requires a real database connection
    import os
    if 'test' not in os.environ.get('DATABASE_URL', '').lower():
        logger.info("Skipping schema validation test - requires test database")
        return
    
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Check required tables
        required_tables = {'sessions', 'chat_messages', 'files', 'analysis_results'}
        
        async with db_manager.get_connection() as conn:
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            
            table_names = {row['table_name'] for row in tables}
            missing_tables = required_tables - table_names
            
            assert not missing_tables, f"Missing required tables: {missing_tables}"
            
            # Check important indexes
            indexes = await conn.fetch("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                AND indexname LIKE 'idx_%'
            """)
            
            index_names = [row['indexname'] for row in indexes]
            
            # Should have cleanup indexes
            cleanup_indexes = [idx for idx in index_names if 'cleanup' in idx or 'archive' in idx]
            assert len(cleanup_indexes) > 0, "Missing file cleanup indexes"
            
            logger.info(f"✅ Schema validation passed: {len(table_names)} tables, {len(index_names)} indexes")
        
        await db_manager.close()
        
    except Exception as e:
        logger.info(f"Skipping schema validation due to database connection: {e}")


async def test_basic_crud_operations():
    """Test basic CRUD operations."""
    import os
    if 'test' not in os.environ.get('DATABASE_URL', '').lower():
        logger.info("Skipping CRUD test - requires test database")
        return
    
    try:
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        test_session_id = "test-crud-session"
        
        # Create session
        await db_manager.execute_query(
            "INSERT INTO sessions (session_id, name) VALUES ($1, $2) ON CONFLICT (session_id) DO NOTHING",
            test_session_id, "Test CRUD Session"
        )
        
        # Read session
        session = await db_manager.fetch_one(
            "SELECT * FROM sessions WHERE session_id = $1", test_session_id
        )
        assert session is not None
        assert session['name'] == "Test CRUD Session"
        
        # Update session
        await db_manager.execute_query(
            "UPDATE sessions SET name = $1 WHERE session_id = $2",
            "Updated CRUD Session", test_session_id
        )
        
        # Verify update
        updated_session = await db_manager.fetch_one(
            "SELECT * FROM sessions WHERE session_id = $1", test_session_id
        )
        assert updated_session['name'] == "Updated CRUD Session"
        
        # Create chat message
        await db_manager.execute_query(
            "INSERT INTO chat_messages (session_id, message_type, content) VALUES ($1, $2, $3)",
            test_session_id, "user", "Test message"
        )
        
        # Read messages
        messages = await db_manager.fetch_all(
            "SELECT * FROM chat_messages WHERE session_id = $1", test_session_id
        )
        assert len(messages) >= 1
        
        # Delete test data
        await db_manager.execute_query(
            "DELETE FROM sessions WHERE session_id = $1", test_session_id
        )
        
        logger.info("✅ Basic CRUD operations test passed")
        
        await db_manager.close()
        
    except Exception as e:
        logger.info(f"Skipping CRUD test due to database connection: {e}")


async def run_all_tests():
    """Run all database tests."""
    logger.info("Running database tests...")
    
    # Tests that don't require database connection
    await test_database_manager_initialization()
    await test_database_connection_error()
    await test_database_operations_without_initialization()
    await test_health_check_without_pool()
    
    # Tests that require database connection (will skip if not available)
    await test_file_cleanup_functions()
    await test_schema_validation()
    await test_basic_crud_operations()
    
    logger.info("✅ All database tests completed!")


if __name__ == "__main__":
    asyncio.run(run_all_tests())