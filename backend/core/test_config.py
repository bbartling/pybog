"""
Test configuration management system.
"""

import os
import pytest
from unittest.mock import patch
from config import (
    ConfigManager, 
    AppConfig, 
    DatabaseConfig, 
    FileRetentionConfig,
    WebSocketConfig,
    LLMConfig,
    ConfigurationError,
    get_config
)


def test_database_config_defaults():
    """Test database configuration with default values."""
    config = DatabaseConfig()
    assert config.url == "postgresql://pybog:pybog123@localhost:5432/pybog"
    assert config.pool_size == 10
    assert config.max_overflow == 20
    assert config.pool_timeout == 30


def test_database_config_validation():
    """Test database URL validation."""
    with pytest.raises(ValueError, match="DATABASE_URL must be a PostgreSQL connection string"):
        DatabaseConfig(url="mysql://invalid")


def test_file_retention_config_defaults():
    """Test file retention configuration with default values."""
    config = FileRetentionConfig()
    assert config.archive_threshold_days == 30
    assert config.purge_threshold_days == 90
    assert config.cleanup_interval_hours == 1
    assert config.max_file_size_mb == 10


def test_file_retention_validation():
    """Test file retention threshold validation."""
    # Test positive days validation
    with pytest.raises(ValueError, match="Threshold days must be positive"):
        FileRetentionConfig(archive_threshold_days=0)
    
    # Test purge after archive validation
    with pytest.raises(ValueError, match="Purge threshold must be greater than archive threshold"):
        FileRetentionConfig(archive_threshold_days=90, purge_threshold_days=30)


def test_websocket_config_defaults():
    """Test WebSocket configuration with default values."""
    config = WebSocketConfig()
    assert config.max_connections_per_session == 5
    assert config.connection_timeout_seconds == 300
    assert config.ping_interval_seconds == 30
    assert config.max_message_size_kb == 1024
    assert config.event_replay_limit == 10


def test_llm_config_defaults():
    """Test LLM configuration with default values."""
    config = LLMConfig()
    assert config.openai_api_key is None
    assert config.model_name == "gpt-3.5-turbo"
    assert config.max_tokens == 2000
    assert config.temperature == 0.7
    assert config.streaming_enabled is True


def test_app_config_defaults():
    """Test main application configuration with default values."""
    config = AppConfig()
    assert config.environment == "development"
    assert config.debug is True
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert "http://localhost:3001" in config.cors_origins


def test_app_config_environment_validation():
    """Test environment validation."""
    with pytest.raises(ValueError, match="Environment must be one of"):
        AppConfig(environment="invalid")


@patch.dict(os.environ, {
    'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',
    'ENVIRONMENT': 'testing',
    'DEBUG': 'false',
    'FILE_ARCHIVE_THRESHOLD_DAYS': '15',
    'FILE_PURGE_THRESHOLD_DAYS': '45',
    'OPENAI_API_KEY': 'test-key'
})
def test_config_from_environment():
    """Test configuration loading from environment variables."""
    config = AppConfig()
    assert config.database.url == 'postgresql://test:test@localhost:5432/test'
    assert config.environment == 'testing'
    assert config.debug is False
    assert config.file_retention.archive_threshold_days == 15
    assert config.file_retention.purge_threshold_days == 45
    assert config.llm.openai_api_key == 'test-key'


def test_config_manager_singleton():
    """Test that ConfigManager is a singleton."""
    manager1 = ConfigManager()
    manager2 = ConfigManager()
    assert manager1 is manager2


def test_config_manager_validation_error():
    """Test configuration validation error handling."""
    with patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'OPENAI_API_KEY': '',  # Missing required key for production
    }):
        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            ConfigManager()._load_config()


def test_config_manager_helper_methods():
    """Test ConfigManager helper methods."""
    manager = ConfigManager()
    
    # Test helper methods
    assert isinstance(manager.get_database_url(), str)
    assert isinstance(manager.get_cors_origins(), list)
    assert isinstance(manager.is_debug_enabled(), bool)
    assert isinstance(manager.get_file_size_limit_bytes(), int)
    
    # Test file size calculation
    expected_bytes = manager.config.file_retention.max_file_size_mb * 1024 * 1024
    assert manager.get_file_size_limit_bytes() == expected_bytes


def test_global_config_functions():
    """Test global configuration accessor functions."""
    config = get_config()
    assert isinstance(config, AppConfig)
    
    from config import (
        get_database_config,
        get_websocket_config, 
        get_file_retention_config,
        get_llm_config
    )
    
    assert isinstance(get_database_config(), DatabaseConfig)
    assert isinstance(get_websocket_config(), WebSocketConfig)
    assert isinstance(get_file_retention_config(), FileRetentionConfig)
    assert isinstance(get_llm_config(), LLMConfig)


if __name__ == "__main__":
    # Run basic validation test
    try:
        config = get_config()
        print(f"✅ Configuration loaded successfully!")
        print(f"   Environment: {config.environment}")
        print(f"   Database URL: {config.database.url}")
        print(f"   Debug mode: {config.debug}")
        print(f"   File size limit: {config.file_retention.max_file_size_mb}MB")
        print(f"   Archive threshold: {config.file_retention.archive_threshold_days} days")
        print(f"   Purge threshold: {config.file_retention.purge_threshold_days} days")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        exit(1)