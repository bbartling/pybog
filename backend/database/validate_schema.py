#!/usr/bin/env python3
"""
Validate the FastAPI database schema without requiring a live database connection.
Checks SQL syntax and schema structure.
"""

import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_sql_syntax(sql_content: str) -> bool:
    """Basic SQL syntax validation."""
    try:
        # Check for basic SQL syntax issues
        errors = []
        
        # Check for unmatched parentheses
        open_parens = sql_content.count('(')
        close_parens = sql_content.count(')')
        if open_parens != close_parens:
            errors.append(f"Unmatched parentheses: {open_parens} open, {close_parens} close")
        
        # Check for required table definitions
        required_tables = ['sessions', 'chat_messages', 'files', 'analysis_results']
        for table in required_tables:
            if f"CREATE TABLE IF NOT EXISTS {table}" not in sql_content:
                errors.append(f"Missing table definition: {table}")
        
        # Check for required indexes
        required_indexes = ['idx_files_cleanup', 'idx_files_archive_candidates', 'idx_files_purge_candidates']
        for index in required_indexes:
            if f"CREATE INDEX IF NOT EXISTS {index}" not in sql_content:
                errors.append(f"Missing required index: {index}")
        
        # Check for required functions
        required_functions = ['archive_old_bytea_files', 'purge_archived_files']
        for function in required_functions:
            if f"CREATE OR REPLACE FUNCTION {function}" not in sql_content:
                errors.append(f"Missing required function: {function}")
        
        # Check for proper foreign key relationships
        fk_patterns = [
            r'session_id TEXT REFERENCES sessions\(session_id\)',
            r'input_file_id INTEGER REFERENCES files\(id\)',
            r'bog_file_id INTEGER REFERENCES files\(id\)'
        ]
        
        for pattern in fk_patterns:
            if not re.search(pattern, sql_content):
                errors.append(f"Missing foreign key pattern: {pattern}")
        
        if errors:
            for error in errors:
                logger.error(f"❌ {error}")
            return False
        
        logger.info("✅ SQL syntax validation passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ SQL validation failed: {e}")
        return False


def validate_schema_structure(sql_content: str) -> bool:
    """Validate the logical structure of the schema."""
    try:
        # Extract table definitions
        table_pattern = r'CREATE TABLE IF NOT EXISTS (\w+) \((.*?)\);'
        tables = re.findall(table_pattern, sql_content, re.DOTALL)
        
        table_info = {}
        for table_name, table_def in tables:
            # Extract column definitions
            columns = []
            for line in table_def.split('\n'):
                line = line.strip()
                if line and not line.startswith('--') and not line.startswith('CONSTRAINT'):
                    # Extract column name (first word)
                    parts = line.split()
                    if parts and not parts[0].upper() in ['PRIMARY', 'FOREIGN', 'CHECK', 'UNIQUE']:
                        col_name = parts[0].replace(',', '')
                        columns.append(col_name)
            
            table_info[table_name] = columns
        
        # Validate table structure
        validations = []
        
        # Sessions table
        if 'sessions' in table_info:
            sessions_cols = table_info['sessions']
            required_cols = ['session_id', 'name', 'metadata', 'created_at', 'updated_at']
            missing = [col for col in required_cols if col not in sessions_cols]
            if missing:
                validations.append(f"Sessions table missing columns: {missing}")
            else:
                validations.append("✅ Sessions table structure valid")
        
        # Chat messages table
        if 'chat_messages' in table_info:
            chat_cols = table_info['chat_messages']
            required_cols = ['id', 'session_id', 'message_type', 'content', 'created_at']
            missing = [col for col in required_cols if col not in chat_cols]
            if missing:
                validations.append(f"Chat_messages table missing columns: {missing}")
            else:
                validations.append("✅ Chat_messages table structure valid")
        
        # Files table
        if 'files' in table_info:
            files_cols = table_info['files']
            required_cols = ['id', 'session_id', 'filename', 'file_data', 'file_path', 'file_size', 'state', 'archived_at']
            missing = [col for col in required_cols if col not in files_cols]
            if missing:
                validations.append(f"Files table missing columns: {missing}")
            else:
                validations.append("✅ Files table structure valid (hybrid BYTEA + file_path)")
        
        # Analysis results table
        if 'analysis_results' in table_info:
            analysis_cols = table_info['analysis_results']
            required_cols = ['id', 'session_id', 'input_file_id', 'bog_file_id', 'state', 'analysis_data']
            missing = [col for col in required_cols if col not in analysis_cols]
            if missing:
                validations.append(f"Analysis_results table missing columns: {missing}")
            else:
                validations.append("✅ Analysis_results table structure valid")
        
        # Log all validations
        for validation in validations:
            if validation.startswith("✅"):
                logger.info(validation)
            else:
                logger.error(f"❌ {validation}")
        
        # Return True if no errors
        return all(v.startswith("✅") for v in validations)
        
    except Exception as e:
        logger.error(f"❌ Schema structure validation failed: {e}")
        return False


def validate_retention_strategy(sql_content: str) -> bool:
    """Validate file retention and cleanup strategy."""
    try:
        validations = []
        
        # Check for archived_at column
        if 'archived_at TIMESTAMPTZ' in sql_content:
            validations.append("✅ archived_at column present for retention strategy")
        else:
            validations.append("❌ Missing archived_at column for retention strategy")
        
        # Check for cleanup indexes
        cleanup_indexes = [
            'idx_files_cleanup',
            'idx_files_archive_candidates', 
            'idx_files_purge_candidates'
        ]
        
        for index in cleanup_indexes:
            if index in sql_content:
                validations.append(f"✅ Cleanup index present: {index}")
            else:
                validations.append(f"❌ Missing cleanup index: {index}")
        
        # Check for cleanup functions
        if 'archive_old_bytea_files' in sql_content and 'purge_archived_files' in sql_content:
            validations.append("✅ File cleanup functions present")
        else:
            validations.append("❌ Missing file cleanup functions")
        
        # Log validations
        for validation in validations:
            if validation.startswith("✅"):
                logger.info(validation)
            else:
                logger.error(validation)
        
        return all(v.startswith("✅") for v in validations)
        
    except Exception as e:
        logger.error(f"❌ Retention strategy validation failed: {e}")
        return False


def main():
    """Main validation function."""
    logger.info("PyBOG FastAPI Database Schema Validation")
    logger.info("=" * 50)
    
    # Read the schema file
    schema_file = Path(__file__).parent / "fastapi_unified_schema.sql"
    
    if not schema_file.exists():
        logger.error(f"❌ Schema file not found: {schema_file}")
        return False
    
    sql_content = schema_file.read_text(encoding='utf-8')
    logger.info(f"📄 Loaded schema file: {schema_file.name} ({len(sql_content)} characters)")
    
    # Run validations
    syntax_valid = validate_sql_syntax(sql_content)
    structure_valid = validate_schema_structure(sql_content)
    retention_valid = validate_retention_strategy(sql_content)
    
    # Summary
    logger.info("=" * 50)
    if syntax_valid and structure_valid and retention_valid:
        logger.info("🎉 Schema validation passed! The FastAPI database schema is ready.")
        return True
    else:
        logger.error("❌ Schema validation failed. Please fix the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)