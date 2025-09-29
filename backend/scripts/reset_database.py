#!/usr/bin/env python3
"""
Database Reset Script
Reinitializes the database and removes all old data for integration testing.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_config
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def drop_and_recreate_database():
    """Drop and recreate the database"""
    config = get_config()
    
    # Parse database URL to get connection details
    db_url = config.database.url
    if not db_url:
        raise ValueError("DATABASE_URL not configured")
    
    # Extract database name and connection details
    import urllib.parse
    parsed = urllib.parse.urlparse(db_url)
    
    db_name = parsed.path[1:]  # Remove leading slash
    host = parsed.hostname
    port = parsed.port or 5432
    username = parsed.username
    password = parsed.password
    
    # If running locally (not in Docker), map postgres hostname to localhost
    if host == 'postgres':
        host = 'localhost'
        port = 5433  # Use Docker exposed port
    
    logger.info(f"Connecting to PostgreSQL server at {host}:{port}")
    logger.info(f"Target database: {db_name}")
    
    # Connect to postgres database (not the target database)
    postgres_conn = await asyncpg.connect(
        host=host,
        port=port,
        user=username,
        password=password,
        database='postgres'
    )
    
    try:
        # Terminate existing connections to the target database
        logger.info(f"Terminating existing connections to {db_name}...")
        await postgres_conn.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{db_name}' AND pid <> pg_backend_pid()
        """)
        
        # Drop the database if it exists
        logger.info(f"Dropping database {db_name}...")
        await postgres_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        
        # Create the database
        logger.info(f"Creating database {db_name}...")
        await postgres_conn.execute(f'CREATE DATABASE "{db_name}"')
        
        logger.info(f"✅ Database {db_name} recreated successfully")
        
    finally:
        await postgres_conn.close()


async def initialize_database_schema():
    """Initialize the database schema"""
    config = get_config()
    
    # Modify database URL for local connection
    db_url = config.database.url
    if 'postgres:5432' in db_url:
        db_url = db_url.replace('postgres:5432', 'localhost:5433')
    
    logger.info("Connecting to the new database...")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Read and execute the database schema
        schema_file = Path(__file__).parent.parent.parent / "init_database.sql"
        if not schema_file.exists():
            # Try alternative location
            schema_file = Path(__file__).parent.parent.parent / "database_schema.sql"
        
        if not schema_file.exists():
            logger.error("Database schema file not found!")
            return False
        
        logger.info(f"Reading schema from: {schema_file}")
        schema_sql = schema_file.read_text(encoding='utf-8')
        
        # Execute schema creation
        logger.info("Creating database schema...")
        await conn.execute(schema_sql)
        
        logger.info("✅ Database schema created successfully")
        
        # Verify tables were created
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables]
        logger.info(f"Created tables: {', '.join(table_names)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        return False
        
    finally:
        await conn.close()


async def verify_database_setup():
    """Verify the database is properly set up"""
    logger.info("Verifying database setup...")
    
    try:
        from core.database import get_database
        
        db = await get_database()
        
        # Test basic connectivity
        result = await db.fetch_val("SELECT 1")
        assert result == 1, "Basic query failed"
        
        # Test health check
        health = await db.health_check()
        assert health["status"] == "healthy", f"Health check failed: {health}"
        
        logger.info("✅ Database verification successful")
        logger.info(f"   Pool size: {health['pool_stats']['size']}")
        logger.info(f"   Available connections: {health['pool_stats']['freesize']}")
        logger.info(f"   Tables: {health['table_counts']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False


async def main():
    """Main database reset process"""
    logger.info("🔄 STARTING DATABASE RESET")
    logger.info("="*50)
    
    try:
        # Step 1: Drop and recreate database
        await drop_and_recreate_database()
        
        # Step 2: Initialize schema
        success = await initialize_database_schema()
        if not success:
            return 1
        
        # Step 3: Verify setup
        success = await verify_database_setup()
        if not success:
            return 1
        
        logger.info("\n🎉 DATABASE RESET COMPLETED SUCCESSFULLY!")
        logger.info("✅ Database is ready for integration testing")
        
        return 0
        
    except Exception as e:
        logger.error(f"💥 Database reset failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)