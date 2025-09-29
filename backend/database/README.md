# PyBOG FastAPI Database Setup

This directory contains the database schema, initialization scripts, and migration tools for the PyBOG FastAPI backend.

## Files Overview

- `fastapi_unified_schema.sql` - Clean unified schema for FastAPI backend
- `init_fastapi_db.py` - Database initialization script
- `migrate_to_fastapi.py` - Migration script from n8n schema to FastAPI schema
- `validate_schema.py` - Schema validation (works without database connection)

## Quick Start

### 1. Validate Schema (No Database Required)

```bash
cd backend
python database/validate_schema.py
```

### 2. Initialize Database (Requires PostgreSQL)

Make sure PostgreSQL is running and update your `.env` file:

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your database credentials
# DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# Initialize the database
python database/init_fastapi_db.py
```

### 3. Migrate from Existing n8n Schema (Optional)

If you have existing data from the n8n-based system:

```bash
python database/migrate_to_fastapi.py
```

## Database Schema

### Core Tables

#### `sessions`
- Primary session management
- Simple session_id (TEXT) primary key
- Metadata stored as JSONB

#### `chat_messages`
- All chat history and conversations
- Links to sessions via session_id
- Supports user, assistant, and system message types

#### `files`
- Hybrid storage: BYTEA for small files (<10MB), file_path for larger files
- State machine: queued → processing → finalizing → complete/failed
- Retention strategy with archived_at column

#### `analysis_results`
- Analysis workflow tracking
- Links input files to generated BOG files
- State machine for progress tracking

### File Retention Strategy

- **Archive**: BYTEA data archived after 30 days (configurable)
- **Purge**: Archived data purged after 90 days (configurable)
- **Indexes**: Optimized for cleanup operations
- **Functions**: `archive_old_bytea_files()` and `purge_archived_files()`

### Key Features

1. **Hybrid File Storage**: Automatic decision between BYTEA and file_path based on file size
2. **State Machine**: Consistent progress tracking across all operations
3. **Cleanup Strategy**: Automated file retention with configurable thresholds
4. **Performance Indexes**: Optimized for common queries and cleanup operations
5. **Views**: Pre-built views for session overview and active analysis

## Configuration

Database settings are managed through the configuration system in `backend/core/config.py`:

```python
# Database connection
DATABASE_URL=postgresql://user:pass@host:port/db

# Connection pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# File retention
FILE_ARCHIVE_THRESHOLD_DAYS=30
FILE_PURGE_THRESHOLD_DAYS=90
MAX_FILE_SIZE_MB=10
```

## Troubleshooting

### Connection Issues

1. **Check PostgreSQL is running**:
   ```bash
   # Windows
   net start postgresql-x64-15
   
   # Linux/Mac
   sudo systemctl start postgresql
   ```

2. **Verify credentials**: Make sure DATABASE_URL in `.env` is correct

3. **Test connection**:
   ```bash
   psql "postgresql://user:pass@localhost:5432/dbname"
   ```

### Schema Issues

1. **Validate schema**: Run `python database/validate_schema.py`
2. **Check logs**: Look for specific error messages in initialization output
3. **Manual schema**: Apply `fastapi_unified_schema.sql` directly if needed

### Migration Issues

1. **Backup first**: Migration script creates backup tables automatically
2. **Check existing data**: Review what tables and data exist before migration
3. **Incremental approach**: Migrate sessions first, then messages, then files

## Development

### Adding New Tables

1. Add table definition to `fastapi_unified_schema.sql`
2. Add appropriate indexes for performance
3. Update validation in `validate_schema.py`
4. Add migration logic if needed

### Testing

```bash
# Validate schema without database
python database/validate_schema.py

# Test with real database (requires test DB)
python core/test_database.py
```

### Performance Monitoring

The schema includes views for monitoring:

- `session_overview` - Session statistics and counts
- `active_analysis` - Currently running analysis processes  
- `file_cleanup_candidates` - Files ready for archival/purge

```sql
-- Check session activity
SELECT * FROM session_overview ORDER BY updated_at DESC LIMIT 10;

-- Monitor active processes
SELECT * FROM active_analysis;

-- Review cleanup candidates
SELECT cleanup_action, COUNT(*) FROM file_cleanup_candidates GROUP BY cleanup_action;
```