"""
Database connection management for PyBOG FastAPI backend.
Handles asyncpg connection pooling, initialization, and migrations.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection
from pathlib import Path

from .config import get_database_config, DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for the FastAPI backend."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or get_database_config()
        self.pool: Optional[Pool] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection pool and run migrations."""
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.config.url,
                min_size=1,
                max_size=self.config.pool_size,
                max_inactive_connection_lifetime=300,
                command_timeout=self.config.pool_timeout
            )
            
            logger.info(f"Database pool created with {self.config.pool_size} connections")
            
            # Test connection
            async with self.pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                logger.info(f"Connected to PostgreSQL: {version}")
            
            # Run initialization and migrations
            await self._run_migrations()
            
            self._initialized = True
            logger.info("Database initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseConnectionError(f"Database initialization failed: {e}")
    
    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self._initialized = False
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if not self.pool:
            raise DatabaseConnectionError("Database not initialized")
        
        async with self.pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database operation failed: {e}")
                raise
    
    async def execute_query(self, query: str, *args) -> str:
        """Execute a query and return the result."""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row as a dictionary."""
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows as a list of dictionaries."""
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetch_val(self, query: str, *args) -> Any:
        """Fetch a single value."""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute_transaction(self, queries: List[tuple]) -> None:
        """Execute multiple queries in a transaction."""
        async with self.get_connection() as conn:
            async with conn.transaction():
                for query, args in queries:
                    await conn.execute(query, *args)
    
    async def _run_migrations(self) -> None:
        """Run database migrations and initialization scripts."""
        try:
            async with self.get_connection() as conn:
                # Check if tables already exist
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                
                table_names = [row['table_name'] for row in tables]
                logger.info(f"Existing tables: {', '.join(table_names)}")
                
                # Verify required tables exist
                required_tables = {'sessions', 'chat_messages', 'files', 'analysis_results'}
                missing_tables = required_tables - set(table_names)
                
                if missing_tables:
                    logger.info(f"Missing tables: {missing_tables}, applying schema...")
                    
                    # Get the database directory path
                    db_dir = Path(__file__).parent.parent / "database"
                    schema_file = db_dir / "fastapi_unified_schema.sql"
                    
                    if not schema_file.exists():
                        raise FileNotFoundError(f"Schema file not found: {schema_file}")
                    
                    # Read and execute the schema
                    schema_sql = schema_file.read_text(encoding='utf-8')
                    
                    # Execute schema in a transaction
                    async with conn.transaction():
                        await conn.execute(schema_sql)
                    
                    logger.info("Database schema applied successfully")
                else:
                    logger.info("All required tables already exist")
                
                # Final verification
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                
                table_names = [row['table_name'] for row in tables]
                missing_tables = required_tables - set(table_names)
                
                if missing_tables:
                    raise DatabaseMigrationError(f"Missing required tables after migration: {missing_tables}")
                
                logger.info("All required tables verified")
        
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise DatabaseMigrationError(f"Failed to run migrations: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database."""
        try:
            if not self.pool:
                return {"status": "error", "message": "Database not initialized"}
            
            async with self.get_connection() as conn:
                # Test basic connectivity
                await conn.fetchval("SELECT 1")
                
                # Get pool stats
                pool_stats = {
                    "size": self.pool.get_size(),
                    "max_size": self.pool.get_max_size(),
                    "min_size": self.pool.get_min_size(),
                    "idle_size": self.pool.get_idle_size()
                }
                
                # Get table counts
                table_counts = {}
                for table in ['sessions', 'chat_messages', 'files', 'analysis_results']:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = count
                
                return {
                    "status": "healthy",
                    "pool_stats": pool_stats,
                    "table_counts": table_counts,
                    "database_url": self.config.url.split('@')[1] if '@' in self.config.url else "hidden"
                }
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def cleanup_old_files(self, archive_days: int = 30, purge_days: int = 90) -> Dict[str, int]:
        """Run file cleanup operations."""
        try:
            async with self.get_connection() as conn:
                # Archive old BYTEA files
                archived_count = await conn.fetchval(
                    "SELECT archive_old_bytea_files($1)", archive_days
                )
                
                # Purge very old archived files
                purged_count = await conn.fetchval(
                    "SELECT purge_archived_files($1)", purge_days
                )
                
                logger.info(f"File cleanup completed: {archived_count} archived, {purged_count} purged")
                
                return {
                    "archived_count": archived_count,
                    "purged_count": purged_count
                }
        
        except Exception as e:
            logger.error(f"File cleanup failed: {e}")
            raise DatabaseOperationError(f"File cleanup failed: {e}")


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class DatabaseMigrationError(Exception):
    """Raised when database migration fails."""
    pass


class DatabaseOperationError(Exception):
    """Raised when database operation fails."""
    pass


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    
    return _db_manager


async def close_database() -> None:
    """Close the global database manager."""
    global _db_manager
    
    if _db_manager:
        await _db_manager.close()
        _db_manager = None


# Convenience functions for common operations
async def execute_query(query: str, *args) -> str:
    """Execute a query using the global database manager."""
    db = await get_database()
    return await db.execute_query(query, *args)


async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Fetch one row using the global database manager."""
    db = await get_database()
    return await db.fetch_one(query, *args)


async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Fetch all rows using the global database manager."""
    db = await get_database()
    return await db.fetch_all(query, *args)


async def fetch_val(query: str, *args) -> Any:
    """Fetch a single value using the global database manager."""
    db = await get_database()
    return await db.fetch_val(query, *args)


async def get_connection():
    """Get a database connection from the global manager."""
    db = await get_database()
    return db.get_connection()