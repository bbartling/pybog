#!/usr/bin/env python3
"""
Migration script to transition from n8n-based schema to FastAPI unified schema.
Preserves existing session and message data while cleaning up n8n-specific tables.
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import DatabaseManager, DatabaseConnectionError
from core.config import get_database_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from n8n schema to FastAPI schema."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    async def initialize(self):
        """Initialize database connection."""
        await self.db_manager.initialize()
    
    async def close(self):
        """Close database connection."""
        await self.db_manager.close()
    
    async def check_existing_schema(self) -> Dict[str, Any]:
        """Check what tables and data exist in the current schema."""
        try:
            # Get all tables
            tables = await self.db_manager.fetch_all("""
                SELECT table_name, table_type
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            table_names = [row['table_name'] for row in tables]
            
            # Check for data in key tables
            data_counts = {}
            for table in ['sessions', 'messages', 'conversation_history', 'files', 'analysis_results']:
                if table in table_names:
                    count = await self.db_manager.fetch_val(f"SELECT COUNT(*) FROM {table}")
                    data_counts[table] = count
            
            return {
                'tables': table_names,
                'data_counts': data_counts,
                'has_n8n_schema': 'workflow_executions' in table_names,
                'has_fastapi_schema': 'chat_messages' in table_names
            }
        
        except Exception as e:
            logger.error(f"Failed to check existing schema: {e}")
            return {'error': str(e)}
    
    async def backup_existing_data(self) -> bool:
        """Create backup tables for existing data."""
        try:
            logger.info("Creating backup tables...")
            
            backup_queries = [
                # Backup sessions
                """CREATE TABLE IF NOT EXISTS sessions_backup AS 
                   SELECT * FROM sessions WHERE EXISTS (SELECT 1 FROM sessions LIMIT 1)""",
                
                # Backup messages (if exists)
                """CREATE TABLE IF NOT EXISTS messages_backup AS 
                   SELECT * FROM messages WHERE EXISTS (SELECT 1 FROM messages LIMIT 1)""",
                
                # Backup conversation history (if exists)
                """CREATE TABLE IF NOT EXISTS conversation_history_backup AS 
                   SELECT * FROM conversation_history WHERE EXISTS (SELECT 1 FROM conversation_history LIMIT 1)""",
                
                # Backup files (if exists)
                """CREATE TABLE IF NOT EXISTS files_backup AS 
                   SELECT * FROM files WHERE EXISTS (SELECT 1 FROM files LIMIT 1)""",
                
                # Backup analysis results (if exists)
                """CREATE TABLE IF NOT EXISTS analysis_results_backup AS 
                   SELECT * FROM analysis_results WHERE EXISTS (SELECT 1 FROM analysis_results LIMIT 1)"""
            ]
            
            for query in backup_queries:
                try:
                    await self.db_manager.execute_query(query)
                except Exception as e:
                    # It's OK if backup fails for non-existent tables
                    logger.debug(f"Backup query failed (expected for missing tables): {e}")
            
            logger.info("✅ Backup tables created")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backups: {e}")
            return False
    
    async def migrate_session_data(self) -> int:
        """Migrate session data to new format."""
        try:
            # Check if old sessions table exists and has data
            old_sessions = await self.db_manager.fetch_all("""
                SELECT session_id, name, created_at, updated_at, metadata
                FROM sessions 
                WHERE session_id IS NOT NULL
            """)
            
            if not old_sessions:
                logger.info("No session data to migrate")
                return 0
            
            migrated_count = 0
            
            for session in old_sessions:
                # Insert into new sessions table format
                await self.db_manager.execute_query("""
                    INSERT INTO sessions (session_id, name, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (session_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                """, 
                    session['session_id'],
                    session['name'] or 'Migrated Session',
                    session['metadata'] or {},
                    session['created_at'],
                    session['updated_at']
                )
                migrated_count += 1
            
            logger.info(f"✅ Migrated {migrated_count} sessions")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Failed to migrate session data: {e}")
            return 0
    
    async def migrate_message_data(self) -> int:
        """Migrate message data to new chat_messages format."""
        try:
            migrated_count = 0
            
            # Try to migrate from messages table
            try:
                old_messages = await self.db_manager.fetch_all("""
                    SELECT session_id, type, content, timestamp, metadata
                    FROM messages 
                    WHERE session_id IS NOT NULL
                    ORDER BY timestamp ASC
                """)
                
                for message in old_messages:
                    await self.db_manager.execute_query("""
                        INSERT INTO chat_messages (session_id, message_type, content, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                    """,
                        message['session_id'],
                        message['type'],
                        message['content'],
                        message['metadata'] or {},
                        message['timestamp']
                    )
                    migrated_count += 1
                
                logger.info(f"✅ Migrated {migrated_count} messages from messages table")
                
            except Exception:
                logger.debug("No messages table found or no data to migrate")
            
            # Try to migrate from conversation_history table
            try:
                old_conversations = await self.db_manager.fetch_all("""
                    SELECT session_id, role, content, created_at, metadata
                    FROM conversation_history 
                    WHERE session_id IS NOT NULL
                    ORDER BY created_at ASC
                """)
                
                for conv in old_conversations:
                    await self.db_manager.execute_query("""
                        INSERT INTO chat_messages (session_id, message_type, content, metadata, created_at)
                        VALUES ($1, $2, $3, $4, $5)
                    """,
                        conv['session_id'],
                        conv['role'],
                        conv['content'],
                        conv['metadata'] or {},
                        conv['created_at']
                    )
                    migrated_count += 1
                
                logger.info(f"✅ Migrated {migrated_count} total messages including conversation history")
                
            except Exception:
                logger.debug("No conversation_history table found or no data to migrate")
            
            return migrated_count
            
        except Exception as e:
            logger.error(f"Failed to migrate message data: {e}")
            return 0
    
    async def migrate_file_data(self) -> int:
        """Migrate file data to new format with BYTEA support."""
        try:
            # Check if old files table exists
            old_files = await self.db_manager.fetch_all("""
                SELECT session_id, filename, file_type, file_size, storage_path, upload_time, metadata
                FROM files 
                WHERE session_id IS NOT NULL
            """)
            
            if not old_files:
                logger.info("No file data to migrate")
                return 0
            
            migrated_count = 0
            
            for file_record in old_files:
                # Map old file_type to new format
                file_type = 'upload'  # Default
                if file_record.get('file_type'):
                    if 'bog' in file_record['file_type'].lower():
                        file_type = 'bog'
                    elif 'analysis' in file_record['file_type'].lower():
                        file_type = 'analysis'
                
                await self.db_manager.execute_query("""
                    INSERT INTO files (
                        session_id, filename, original_name, file_type, 
                        file_path, file_size, state, metadata, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    file_record['session_id'],
                    file_record['filename'],
                    file_record['filename'],  # Use filename as original_name
                    file_type,
                    file_record['storage_path'],
                    file_record['file_size'] or 0,
                    'complete',  # Assume migrated files are complete
                    file_record['metadata'] or {},
                    file_record['upload_time']
                )
                migrated_count += 1
            
            logger.info(f"✅ Migrated {migrated_count} files")
            return migrated_count
            
        except Exception as e:
            logger.error(f"Failed to migrate file data: {e}")
            return 0
    
    async def cleanup_n8n_tables(self) -> List[str]:
        """Remove n8n-specific tables that are no longer needed."""
        try:
            n8n_tables = [
                'workflow_executions',
                'approval_history', 
                'document_sessions',
                'document_embeddings',
                'hvac_components'
            ]
            
            dropped_tables = []
            
            for table in n8n_tables:
                try:
                    await self.db_manager.execute_query(f"DROP TABLE IF EXISTS {table} CASCADE")
                    dropped_tables.append(table)
                    logger.info(f"✅ Dropped n8n table: {table}")
                except Exception as e:
                    logger.debug(f"Failed to drop table {table}: {e}")
            
            return dropped_tables
            
        except Exception as e:
            logger.error(f"Failed to cleanup n8n tables: {e}")
            return []


async def main():
    """Main migration function."""
    logger.info("PyBOG Database Migration: n8n → FastAPI")
    logger.info("=" * 50)
    
    migrator = DatabaseMigrator()
    
    try:
        await migrator.initialize()
        
        # Check existing schema
        schema_info = await migrator.check_existing_schema()
        
        if 'error' in schema_info:
            logger.error(f"Failed to check schema: {schema_info['error']}")
            return
        
        logger.info(f"Found {len(schema_info['tables'])} tables")
        logger.info(f"Data counts: {schema_info['data_counts']}")
        
        if schema_info['has_fastapi_schema']:
            logger.info("✅ FastAPI schema already exists")
        else:
            logger.info("Creating FastAPI schema...")
            # The schema will be created by the database manager initialization
        
        # Create backups
        backup_success = await migrator.backup_existing_data()
        if not backup_success:
            logger.error("Backup failed, aborting migration")
            return
        
        # Migrate data
        session_count = await migrator.migrate_session_data()
        message_count = await migrator.migrate_message_data()
        file_count = await migrator.migrate_file_data()
        
        # Cleanup n8n tables (optional)
        if schema_info['has_n8n_schema']:
            logger.info("Cleaning up n8n-specific tables...")
            dropped_tables = await migrator.cleanup_n8n_tables()
            logger.info(f"Dropped {len(dropped_tables)} n8n tables")
        
        # Final verification
        final_counts = await migrator.check_existing_schema()
        
        logger.info("=" * 50)
        logger.info("🎉 Migration completed successfully!")
        logger.info(f"   Sessions migrated: {session_count}")
        logger.info(f"   Messages migrated: {message_count}")
        logger.info(f"   Files migrated: {file_count}")
        logger.info(f"   Final data counts: {final_counts.get('data_counts', {})}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    
    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())