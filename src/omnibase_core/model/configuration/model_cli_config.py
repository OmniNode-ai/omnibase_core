"""
CLI Configuration models for ONEX production deployment.

Provides centralized configuration models with environment variable support,
validation, and default value management for production CLI operations.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ModelTierConfig(BaseModel):
    """Configuration for processing tiers and model availability."""

    local_small: str = Field(default="llama3.2:1b", description="Small local model")
    local_medium: str = Field(default="llama3.2:3b", description="Medium local model")
    local_large: str = Field(default="llama3.2:8b", description="Large local model")
    local_huge: str = Field(default="llama3.2:70b", description="Huge local model")
    cloud_gpt: str = Field(default="gpt-4o", description="Cloud GPT model")
    cloud_claude: str = Field(
        default="claude-3-5-sonnet-20241022", description="Cloud Claude model"
    )

    timeout_seconds: int = Field(default=300, description="Processing timeout")
    retry_attempts: int = Field(default=3, description="Retry attempts")


class ModelOutputConfig(BaseModel):
    """Output formatting and destination configuration."""

    format: str = Field(default="json", description="Output format (json|yaml|text)")
    colored: bool = Field(default=True, description="Enable colored output")
    progress_bars: bool = Field(default=True, description="Show progress bars")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        allowed = {"json", "yaml", "text"}
        if v not in allowed:
            raise ValueError(f"format must be one of {allowed}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v


class ModelAPIConfig(BaseModel):
    """API server configuration for REST interface."""

    host: str = Field(default="localhost", description="API host")
    port: int = Field(default=8000, description="API port")
    workers: int = Field(default=4, description="Number of workers")
    reload: bool = Field(default=False, description="Enable auto-reload")

    # Security
    api_key: Optional[str] = Field(
        default=None, description="API key for authentication"
    )
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")

    # Performance
    max_concurrent_requests: int = Field(
        default=100, description="Max concurrent requests"
    )
    request_timeout: int = Field(default=300, description="Request timeout seconds")


class ModelDatabaseConfig(BaseModel):
    """Database configuration for persistent storage."""

    url: str = Field(default="postgresql://localhost/onex", description="Database URL")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max pool overflow")
    pool_timeout: int = Field(default=30, description="Pool timeout seconds")


class ModelMonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""

    prometheus_enabled: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")

    jaeger_enabled: bool = Field(default=False, description="Enable Jaeger tracing")
    jaeger_endpoint: Optional[str] = Field(default=None, description="Jaeger endpoint")

    sentry_enabled: bool = Field(
        default=False, description="Enable Sentry error tracking"
    )
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN")


class ModelCLIConfig(BaseModel):
    """
    Complete CLI configuration with production settings.

    Supports environment variable overrides and validation for all
    configuration sections used by the production CLI.
    """

    # Core configuration sections
    tiers: ModelTierConfig = Field(default_factory=ModelTierConfig)
    output: ModelOutputConfig = Field(default_factory=ModelOutputConfig)
    api: ModelAPIConfig = Field(default_factory=ModelAPIConfig)
    database: ModelDatabaseConfig = Field(default_factory=ModelDatabaseConfig)
    monitoring: ModelMonitoringConfig = Field(default_factory=ModelMonitoringConfig)

    # Global settings
    config_dir: Path = Field(
        default=Path.home() / ".onex", description="Config directory"
    )
    data_dir: Path = Field(
        default=Path.home() / ".onex" / "data", description="Data directory"
    )
    cache_dir: Path = Field(
        default=Path.home() / ".onex" / "cache", description="Cache directory"
    )

    # Environment overrides
    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose output")

    def model_post_init(self, __context) -> None:
        """Initialize configuration after model creation."""
        self.ensure_directories_exist()

    def ensure_directories_exist(self) -> None:
        """Create configuration directories if they don't exist."""
        for directory in [self.config_dir, self.data_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_file(cls, config_path: Path) -> "ModelCLIConfig":
        """Load configuration from file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # In a real implementation, you would load from YAML/JSON here
        # For now, return defaults
        return cls()

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # In a real implementation, you would save to YAML/JSON here
        # This is a placeholder for the actual serialization logic
        pass

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get the default configuration file path."""
        return Path.home() / ".onex" / "config.yaml"

    @classmethod
    def load_or_create_default(cls) -> "ModelCLIConfig":
        """Load config from default location or create with defaults."""
        config_path = cls.get_default_config_path()

        if config_path.exists():
            return cls.from_file(config_path)

        # Create default config
        config = cls()
        config.save_to_file(config_path)
        return config
