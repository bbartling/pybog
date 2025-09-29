#!/usr/bin/env python3
"""
Database initialization script for PyBOG FastAPI backend.
Creates the database, applies schema, and sets up initial data.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the backend directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager, DatabaseConnectionError
from core.config import get_database_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize the database with schema and sample data."""
    try:
        logger.info("Starting database initialization...")
        
        # Get database configuration
        config = get_database_config()
        logger.info(f"Using database URL: {config.url.split('@')[1] if '@' in config.url else 'hidden'}")
        
        # Create database manager and initialize
        db_manager = DatabaseManager(config)
        await db_manager.initialize()
        
        # Run health check
        health = await db_manager.health_check()
        logger.info(f"Database health check: {health}")
        
        if health['status'] == 'healthy':
            logger.info("✅ Database initialization completed successfully!")
            
            # Print table counts
            table_counts = health.get('table_counts', {})
            for table, count in table_counts.items():
                logger.info(f"   {table}: {count} records")
            
            # Print pool stats
            pool_stats = health.get('pool_stats', {})
            logger.info(f"   Connection pool: {pool_stats.get('size', 0)}/{pool_stats.get('max_size', 0)} connections")
        
        else:
            logger.error(f"❌ Database health check failed: {health.get('message', 'Unknown error')}")
            return False
        
        # Close the database connection
        await db_manager.close()
        return True
        
    except DatabaseConnectionError as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


async def test_database_operations():
    """Test basic database operations."""
    try:
        logger.info("Testing database operations...")
        
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Test session creation
        session_id = "test-init-session"
        await db_manager.execute_query(
            "INSERT INTO sessions (session_id, name, metadata) VALUES ($1, $2, $3) ON CONFLICT (session_id) DO NOTHING",
            session_id, "Test Initialization Session", '{"test": true}'
        )
        
        # Test session retrieval
        session = await db_manager.fetch_one(
            "SELECT * FROM sessions WHERE session_id = $1", session_id
        )
        
        if session:
            logger.info(f"✅ Session created and retrieved: {session['name']}")
        else:
            logger.error("❌ Failed to create or retrieve session")
            return False
        
        # Test chat message creation
        await db_manager.execute_query(
            "INSERT INTO chat_messages (session_id, message_type, content) VALUES ($1, $2, $3)",
            session_id, "system", "Database initialization test message"
        )
        
        # Test message retrieval
        messages = await db_manager.fetch_all(
            "SELECT * FROM chat_messages WHERE session_id = $1", session_id
        )
        
        logger.info(f"✅ Chat messages: {len(messages)} found")
        
        # Test file record creation (without actual file data)
        await db_manager.execute_query(
            """INSERT INTO files (session_id, filename, original_name, file_type, file_size, state) 
               VALUES ($1, $2, $3, $4, $5, $6)""",
            session_id, "test.txt", "test.txt", "upload", 1024, "complete"
        )
        
        # Test file retrieval
        files = await db_manager.fetch_all(
            "SELECT * FROM files WHERE session_id = $1", session_id
        )
        
        logger.info(f"✅ Files: {len(files)} found")
        
        # Test cleanup functions
        cleanup_result = await db_manager.cleanup_old_files(archive_days=30, purge_days=90)
        logger.info(f"✅ Cleanup test: {cleanup_result}")
        
        # Clean up test data
        await db_manager.execute_query(
            "DELETE FROM sessions WHERE session_id = $1", session_id
        )
        
        logger.info("✅ All database operations tested successfully!")
        
        await db_manager.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database operation test failed: {e}")
        return False


async def main():
    """Main initialization function."""
    logger.info("PyBOG FastAPI Database Initialization")
    logger.info("=" * 50)
    
    # Initialize database
    init_success = await init_database()
    if not init_success:
        logger.error("Database initialization failed")
        sys.exit(1)
    
    # Test operations
    test_success = await test_database_operations()
    if not test_success:
        logger.error("Database operation tests failed")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("🎉 Database initialization and testing completed successfully!")
    logger.info("The FastAPI backend is ready to use the database.")


if __name__ == "__main__":
    asyncio.run(main())