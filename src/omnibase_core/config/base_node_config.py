"""
Base node configuration model for ONEX nodes.

This module provides the ModelBaseNodeConfig class that standardizes configuration
management across all ONEX node types with validation, defaults, and type safety.

Author: ONEX Framework Team
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.node import EnumNodeType


class ModelBaseNodeConfig(BaseModel):
    """
    Base configuration model for all ONEX nodes.

    Pure Pydantic model that provides standardized configuration structure
    with validation, defaults, and type safety for consistent node initialization
    across the ONEX architecture.

    This model serves as the foundation for all node-specific
    configuration models and ensures compliance with ONEX
    configuration standards.

    Full YAML and JSON Support:
        This model provides complete YAML and JSON support through Pydantic's
        native capabilities:

        Loading from YAML:
            import yaml
            data = yaml.safe_load(Path("config.yaml").read_text())
            config = ModelBaseNodeConfig(**data)

        Saving to YAML:
            yaml_string = yaml.dump(config.model_dump())
            Path("config.yaml").write_text(yaml_string)

        Loading from JSON:
            config = ModelBaseNodeConfig.model_validate_json(
                Path("config.json").read_text()
            )

        Saving to JSON:
            Path("config.json").write_text(config.model_dump_json(indent=2))
    """

    model_config = ConfigDict(
        extra="ignore",  # Ignore unknown fields for forward compatibility
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        frozen=False,  # Allow updates after initialization
    )

    # Core node identification
    node_id: str = Field(
        ...,
        description="Unique identifier for this node instance",
        min_length=1,
        max_length=255,
    )

    node_name: str = Field(
        default="",
        description="Human-readable name for this node",
        min_length=1,
        max_length=255,
    )

    node_type: EnumNodeType = Field(
        default=EnumNodeType.COMPUTE,
        description="ONEX node type classification",
    )

    node_version: str = Field(
        default="1.0.0",
        description="Version of this node implementation",
        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)*$",
    )

    # Logging configuration
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Default logging level for this node",
    )

    log_format: str = Field(
        default="structured",
        description="Logging format (structured, text, json)",
        pattern=r"^(structured|text|json)$",
    )

    log_to_console: bool = Field(
        default=True,
        description="Whether to log to console output",
    )

    log_to_file: bool = Field(
        default=False,
        description="Whether to log to file output",
    )

    log_file_path: Path | None = Field(
        default=None,
        description="Path to log file (if log_to_file is True)",
    )

    # Performance configuration
    max_concurrent_operations: int = Field(
        default=10,
        description="Maximum number of concurrent operations",
        ge=1,
        le=1000,
    )

    operation_timeout_seconds: float = Field(
        default=30.0,
        description="Default timeout for operations in seconds",
        gt=0.0,
        le=3600.0,
    )

    enable_metrics: bool = Field(
        default=True,
        description="Whether to enable metrics collection",
    )

    # Health check configuration
    health_check_enabled: bool = Field(
        default=True,
        description="Whether to enable health check endpoint",
    )

    health_check_interval_seconds: float = Field(
        default=30.0,
        description="Interval between health checks in seconds",
        gt=0.0,
        le=3600.0,
    )

    # Circuit breaker configuration
    enable_circuit_breaker: bool = Field(
        default=False,
        description="Whether to enable circuit breaker protection",
    )

    circuit_breaker_failure_threshold: int = Field(
        default=5,
        description="Number of failures before opening circuit breaker",
        ge=1,
        le=100,
    )

    circuit_breaker_recovery_timeout_seconds: float = Field(
        default=60.0,
        description="Timeout before attempting circuit breaker recovery",
        gt=0.0,
        le=3600.0,
    )

    # Resource limits
    max_memory_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in MB (None for unlimited)",
        gt=0,
    )

    max_cpu_percent: float | None = Field(
        default=None,
        description="Maximum CPU usage percentage (None for unlimited)",
        gt=0.0,
        le=100.0,
    )

    # Development and debugging
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode with additional logging and checks",
    )

    development_mode: bool = Field(
        default=False,
        description="Enable development mode with relaxed validation",
    )

    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling",
    )

    # Extension points
    custom_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom configuration values for node-specific needs",
    )

    environment_variables: list[str] = Field(
        default_factory=list,
        description="Required environment variables for this node",
    )

    @field_validator("node_id")
    @classmethod
    def validate_node_id(cls, v: str) -> str:
        """Validate node_id format and uniqueness constraints."""
        if not v:
            msg = "node_id cannot be empty"
            raise ValueError(msg)

        # Basic format validation
        if not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            msg = (
                "node_id must contain only alphanumeric characters, hyphens, "
                "underscores, and dots"
            )
            raise ValueError(msg)

        return v

    @field_validator("log_file_path")
    @classmethod
    def validate_log_file_path(cls, v: Path | None, info) -> Path | None:
        """Validate log file path when logging to file is enabled."""
        # Get log_to_file from the validation context (Pydantic v2 pattern)
        log_to_file = False
        if hasattr(info, "data") and info.data is not None:
            log_to_file = info.data.get("log_to_file", False)

        if log_to_file and v is None:
            msg = "log_file_path must be specified when log_to_file is True"
            raise ValueError(msg)

        # Note: Directory creation moved to post-validation initialization
        # to avoid side effects during validation
        if v is not None and not v.parent.exists() and not v.parent.is_absolute():
            # Only validate that the parent path is valid, don't create it yet
            msg = "log_file_path must be an absolute path"
            raise ValueError(msg)

        return v

    @field_validator("custom_config")
    @classmethod
    def validate_custom_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate custom configuration values."""
        # Ensure all keys are valid Python identifiers
        for key in v:
            if not isinstance(key, str) or not key.isidentifier():
                msg = f"Custom config key '{key}' must be a valid Python identifier"
                raise ValueError(msg)

        return v

    def get_custom_config(self, key: str, default: Any = None) -> Any:
        """
        Get a custom configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.custom_config.get(key, default)

    def initialize_log_directory(self) -> None:
        """
        Initialize log file directory after validation.

        Call this method after model creation to ensure log directories exist.
        Separated from validation to avoid side effects during field validation.

        Raises:
            OnexError: If directory cannot be created
        """
        if self.log_to_file and self.log_file_path is not None:
            try:
                self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise OnexError(
                    message=f"Cannot create log file directory: {e}",
                    error_code=CoreErrorCode.INVALID_PARAMETER,
                    context={
                        "log_file_path": str(self.log_file_path),
                        "parent_directory": str(self.log_file_path.parent),
                    },
                ) from e

    def set_custom_config(self, key: str, value: Any) -> None:
        """
        Set a custom configuration value.

        Args:
            key: Configuration key (must be valid Python identifier)
            value: Configuration value

        Raises:
            OnexError: If key is invalid
        """
        if not key.isidentifier():
            raise OnexError(
                message=f"Custom config key '{key}' must be a valid Python identifier",
                error_code=CoreErrorCode.INVALID_PARAMETER,
                context={"key": key},
            )

        self.custom_config[key] = value

    def validate_environment(self) -> list[str]:
        """
        Validate required environment variables are present.

        Returns:
            List of missing environment variables (empty if all present)
        """
        import os

        missing_vars = []
        for var_name in self.environment_variables:
            if var_name not in os.environ:
                missing_vars.append(var_name)

        return missing_vars

    def is_production_mode(self) -> bool:
        """
        Check if node is running in production mode.

        Returns:
            True if not in debug or development mode
        """
        return not (self.debug_mode or self.development_mode)

    def get_effective_log_level(self) -> LogLevel:
        """
        Get effective log level considering debug and development modes.

        Returns:
            Effective log level
        """
        if self.debug_mode:
            return LogLevel.DEBUG

        # Get the enum values for comparison
        current_level = (
            self.log_level
            if isinstance(self.log_level, LogLevel)
            else LogLevel(self.log_level)
        )
        info_level = LogLevel.INFO

        # Compare enum members by their order in definition
        log_levels_order = list(LogLevel)
        current_level_index = log_levels_order.index(current_level)
        info_level_index = log_levels_order.index(info_level)

        if self.development_mode and current_level_index > info_level_index:
            return LogLevel.INFO
        return current_level
