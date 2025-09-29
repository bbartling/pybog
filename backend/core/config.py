"""
Configuration management system for PyBOG backend.
Handles environment variables, database connection settings, and application configuration.
"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
import logging
from dotenv import load_dotenv

# Load environment variables from .env files (only if not already set)
# This ensures Docker environment variables take precedence
load_dotenv('.env', override=False)  # Load from backend/.env
load_dotenv('../.env', override=False)  # Load from root .env

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""
    
    url: str = Field(
        default="postgresql://pybog:pybog123@postgres:5432/pybog",
        env="DATABASE_URL",
        description="PostgreSQL connection URL"
    )
    pool_size: int = Field(
        default=10,
        env="DB_POOL_SIZE", 
        description="Database connection pool size"
    )
    max_overflow: int = Field(
        default=20,
        env="DB_MAX_OVERFLOW",
        description="Maximum overflow connections"
    )
    pool_timeout: int = Field(
        default=30,
        env="DB_POOL_TIMEOUT",
        description="Connection pool timeout in seconds"
    )
    
    @field_validator('url')
    @classmethod
    def validate_database_url(cls, v):
        if not v.startswith('postgresql://'):
            raise ValueError('DATABASE_URL must be a PostgreSQL connection string')
        return v


class FileRetentionConfig(BaseSettings):
    """File cleanup and retention configuration."""
    
    archive_threshold_days: int = Field(
        default=30,
        env="FILE_ARCHIVE_THRESHOLD_DAYS",
        description="Days after which BYTEA files are archived"
    )
    purge_threshold_days: int = Field(
        default=90,
        env="FILE_PURGE_THRESHOLD_DAYS", 
        description="Days after which archived files are purged"
    )
    cleanup_interval_hours: int = Field(
        default=1,
        env="FILE_CLEANUP_INTERVAL_HOURS",
        description="Hours between cleanup task runs"
    )
    max_file_size_mb: int = Field(
        default=10,
        env="MAX_FILE_SIZE_MB",
        description="Maximum file size for BYTEA storage (MB)"
    )
    
    @field_validator('archive_threshold_days', 'purge_threshold_days')
    @classmethod
    def validate_positive_days(cls, v):
        if v <= 0:
            raise ValueError('Threshold days must be positive')
        return v
    
    def model_post_init(self, __context):
        """Validate purge threshold is greater than archive threshold."""
        if self.purge_threshold_days <= self.archive_threshold_days:
            raise ValueError('Purge threshold must be greater than archive threshold')


class WebSocketConfig(BaseSettings):
    """WebSocket connection and streaming configuration."""
    
    max_connections_per_session: int = Field(
        default=5,
        env="WS_MAX_CONNECTIONS_PER_SESSION",
        description="Maximum WebSocket connections per session"
    )
    connection_timeout_seconds: int = Field(
        default=300,
        env="WS_CONNECTION_TIMEOUT_SECONDS", 
        description="WebSocket connection timeout"
    )
    ping_interval_seconds: int = Field(
        default=30,
        env="WS_PING_INTERVAL_SECONDS",
        description="WebSocket ping interval"
    )
    max_message_size_kb: int = Field(
        default=1024,
        env="WS_MAX_MESSAGE_SIZE_KB",
        description="Maximum WebSocket message size (KB)"
    )
    event_replay_limit: int = Field(
        default=10,
        env="WS_EVENT_REPLAY_LIMIT",
        description="Maximum events to replay on session resume"
    )


class LLMConfig(BaseSettings):
    """LangChain and LLM configuration."""
    
    openai_api_key: Optional[str] = Field(
        default=None,
        env="OPENAI_API_KEY",
        description="OpenAI API key for LangChain"
    )
    model_name: str = Field(
        default="gpt-4o-mini",
        env="LLM_MODEL_NAME",
        description="LLM model name"
    )
    max_tokens: int = Field(
        default=2000,
        env="LLM_MAX_TOKENS",
        description="Maximum tokens per LLM response"
    )
    temperature: float = Field(
        default=0.7,
        env="LLM_TEMPERATURE",
        description="LLM temperature setting"
    )
    streaming_enabled: bool = Field(
        default=True,
        env="LLM_STREAMING_ENABLED",
        description="Enable streaming responses"
    )


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Environment
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Application environment (development, production, testing)"
    )
    debug: bool = Field(
        default=True,
        env="DEBUG",
        description="Enable debug mode"
    )
    
    # Server settings
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="Server host"
    )
    port: int = Field(
        default=8000,
        env="PORT",
        description="Server port"
    )
    
    # CORS settings
    cors_origins: str = Field(
        default="http://localhost:3001,http://localhost:3000",
        env="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    
    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    file_retention: FileRetentionConfig = FileRetentionConfig()
    websocket: WebSocketConfig = WebSocketConfig()
    llm: LLMConfig = LLMConfig()
    
    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v):
        return [origin.strip() for origin in v.split(',') if origin.strip()]
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        valid_envs = ['development', 'production', 'testing']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v
    
    class Config:
        env_file = ['.env', '../.env']  # Check both backend/.env and root .env
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from legacy .env


class ConfigManager:
    """Centralized configuration manager with validation and error handling."""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
    
    def _load_config(self) -> None:
        """Load and validate configuration from environment variables."""
        try:
            self._config = AppConfig()
            logger.info(f"Configuration loaded successfully for environment: {self._config.environment}")
            self._validate_required_settings()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration validation failed: {e}")
    
    def _validate_required_settings(self) -> None:
        """Validate that all required settings are present and valid."""
        errors = []
        
        # Validate database URL is accessible
        if not self._config.database.url:
            errors.append("DATABASE_URL is required")
        
        # Validate LLM configuration for production
        if self._config.environment == 'production':
            if not self._config.llm.openai_api_key:
                errors.append("OPENAI_API_KEY is required in production environment")
        
        # Validate file retention logic
        if self._config.file_retention.purge_threshold_days <= self._config.file_retention.archive_threshold_days:
            errors.append("FILE_PURGE_THRESHOLD_DAYS must be greater than FILE_ARCHIVE_THRESHOLD_DAYS")
        
        if errors:
            raise ConfigurationError(f"Configuration validation errors: {'; '.join(errors)}")
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        if self._config is None:
            self._load_config()
        return self._config
    
    def reload(self) -> None:
        """Reload configuration from environment variables."""
        self._config = None
        self._load_config()
    
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        return self.config.database.url
    
    def get_cors_origins(self) -> list:
        """Get the list of allowed CORS origins."""
        return self.config.cors_origins
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.config.debug
    
    def get_file_size_limit_bytes(self) -> int:
        """Get the file size limit for BYTEA storage in bytes."""
        return self.config.file_retention.max_file_size_mb * 1024 * 1024


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config_manager.config


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return config_manager.config.database


def get_websocket_config() -> WebSocketConfig:
    """Get WebSocket configuration."""
    return config_manager.config.websocket


def get_file_retention_config() -> FileRetentionConfig:
    """Get file retention configuration."""
    return config_manager.config.file_retention


def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return config_manager.config.llm