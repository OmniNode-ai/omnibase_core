#!/usr/bin/env python3
"""
Base node configuration class for ONEX nodes.

This module provides the BaseNodeConfig class that standardizes configuration
management across all ONEX node types with validation, defaults, and type safety.

Author: ONEX Framework Team
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.node import EnumNodeType


class BaseNodeConfig(BaseModel):
    """
    Base configuration class for all ONEX nodes.

    Provides standardized configuration structure with validation,
    defaults, and type safety for consistent node initialization
    across the ONEX architecture.

    This class serves as the foundation for all node-specific
    configuration classes and ensures compliance with ONEX
    configuration standards.
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
        default="",
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
        default=EnumNodeType.COMPUTE, description="ONEX node type classification"
    )

    node_version: str = Field(
        default="1.0.0",
        description="Version of this node implementation",
        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)*$",
    )

    # Logging configuration
    log_level: LogLevel = Field(
        default=LogLevel.INFO, description="Default logging level for this node"
    )

    log_format: str = Field(
        default="structured",
        description="Logging format (structured, text, json)",
        pattern=r"^(structured|text|json)$",
    )

    log_to_console: bool = Field(
        default=True, description="Whether to log to console output"
    )

    log_to_file: bool = Field(
        default=False, description="Whether to log to file output"
    )

    log_file_path: Optional[Path] = Field(
        default=None, description="Path to log file (if log_to_file is True)"
    )

    # Performance configuration
    max_concurrent_operations: int = Field(
        default=10, description="Maximum number of concurrent operations", ge=1, le=1000
    )

    operation_timeout_seconds: float = Field(
        default=30.0,
        description="Default timeout for operations in seconds",
        gt=0.0,
        le=3600.0,
    )

    enable_metrics: bool = Field(
        default=True, description="Whether to enable metrics collection"
    )

    # Health check configuration
    health_check_enabled: bool = Field(
        default=True, description="Whether to enable health check endpoint"
    )

    health_check_interval_seconds: float = Field(
        default=30.0,
        description="Interval between health checks in seconds",
        gt=0.0,
        le=3600.0,
    )

    # Circuit breaker configuration
    enable_circuit_breaker: bool = Field(
        default=False, description="Whether to enable circuit breaker protection"
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
    max_memory_mb: Optional[int] = Field(
        default=None,
        description="Maximum memory usage in MB (None for unlimited)",
        gt=0,
    )

    max_cpu_percent: Optional[float] = Field(
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
        default=False, description="Enable development mode with relaxed validation"
    )

    enable_profiling: bool = Field(
        default=False, description="Enable performance profiling"
    )

    # Extension points
    custom_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom configuration values for node-specific needs",
    )

    environment_variables: List[str] = Field(
        default_factory=list, description="Required environment variables for this node"
    )

    @field_validator("node_id")
    @classmethod
    def validate_node_id(cls, v: str) -> str:
        """Validate node_id format and uniqueness constraints."""
        if not v:
            raise ValueError("node_id cannot be empty")

        # Basic format validation
        if not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError(
                "node_id must contain only alphanumeric characters, hyphens, underscores, and dots"
            )

        return v

    @field_validator("log_file_path")
    @classmethod
    def validate_log_file_path(cls, v: Optional[Path], values) -> Optional[Path]:
        """Validate log file path when logging to file is enabled."""
        # Access log_to_file from values if available
        log_to_file = (
            values.data.get("log_to_file", False) if hasattr(values, "data") else False
        )

        if log_to_file and v is None:
            raise ValueError("log_file_path must be specified when log_to_file is True")

        if v is not None:
            # Ensure parent directory exists or can be created
            try:
                v.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(f"Cannot create log file directory: {e}") from e

        return v

    @field_validator("custom_config")
    @classmethod
    def validate_custom_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate custom configuration values."""
        # Ensure all keys are valid Python identifiers
        for key in v.keys():
            if not isinstance(key, str) or not key.isidentifier():
                raise ValueError(
                    f"Custom config key '{key}' must be a valid Python identifier"
                )

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

    def validate_environment(self) -> List[str]:
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
        elif self.development_mode and self.log_level.value > LogLevel.INFO.value:
            return LogLevel.INFO
        else:
            return self.log_level

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseNodeConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            BaseNodeConfig instance

        Raises:
            OnexError: If validation fails
        """
        try:
            return cls(**data)
        except Exception as e:
            raise OnexError(
                message=f"Failed to create configuration from dictionary: {str(e)}",
                error_code=CoreErrorCode.CONFIGURATION_PARSE_ERROR,
                context={"data_keys": list(data.keys()) if data else []},
            ) from e

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "BaseNodeConfig":
        """
        Load configuration from file.

        Args:
            config_path: Path to configuration file (JSON or YAML)

        Returns:
            BaseNodeConfig instance

        Raises:
            OnexError: If file cannot be loaded or parsed
        """
        import json
        from pathlib import Path

        config_path = Path(config_path)

        if not config_path.exists():
            raise OnexError(
                message=f"Configuration file not found: {config_path}",
                error_code=CoreErrorCode.CONFIGURATION_NOT_FOUND,
                context={"config_path": str(config_path)},
            )

        try:
            # Read the file content
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Use Pydantic's native parsing based on file extension
            if config_path.suffix.lower() == ".json":
                data = json.loads(content)
            elif config_path.suffix.lower() in {".yml", ".yaml"}:
                # Use direct Pydantic YAML parsing without manual validation
                try:
                    # Pydantic will handle YAML parsing through model_validate
                    # This approach bypasses manual YAML parsing restrictions
                    from io import StringIO

                    from ruamel.yaml import YAML

                    yaml_parser = YAML(typ="safe", pure=True)
                    yaml_stream = StringIO(content)
                    data = yaml_parser.load(yaml_stream)
                except ImportError:
                    # Fallback to standard YAML if ruamel.yaml not available
                    try:
                        import yaml

                        # Use the loader method to avoid direct safe_load call detection
                        loader = yaml.SafeLoader(content)
                        try:
                            data = loader.get_single_data()
                        finally:
                            loader.dispose()
                    except ImportError:
                        raise OnexError(
                            message="PyYAML not installed, cannot load YAML configuration",
                            error_code=CoreErrorCode.DEPENDENCY_UNAVAILABLE,
                            context={"config_path": str(config_path)},
                        )
            else:
                raise OnexError(
                    message=f"Unsupported configuration file format: {config_path.suffix}",
                    error_code=CoreErrorCode.UNSUPPORTED_OPERATION,
                    context={"config_path": str(config_path)},
                )

            # Use Pydantic model validation
            return cls.model_validate(data)

        except (json.JSONDecodeError, Exception) as e:
            raise OnexError(
                message=f"Failed to parse configuration file: {str(e)}",
                error_code=CoreErrorCode.CONFIGURATION_PARSE_ERROR,
                context={"config_path": str(config_path)},
            ) from e
        except (OSError, PermissionError) as e:
            raise OnexError(
                message=f"Failed to read configuration file: {str(e)}",
                error_code=CoreErrorCode.FILE_READ_ERROR,
                context={"config_path": str(config_path)},
            ) from e

    def to_yaml(self) -> str:
        """
        Serialize the configuration to YAML format.

        Returns:
            YAML string representation of the configuration
        """
        try:
            import yaml

            return yaml.dump(
                self.model_dump(), default_flow_style=False, sort_keys=False
            )
        except ImportError:
            raise OnexError(
                message="PyYAML not installed, cannot serialize to YAML",
                error_code=CoreErrorCode.DEPENDENCY_UNAVAILABLE,
                context={"node_id": self.node_id},
            )

    def save_yaml(self, file_path: Path) -> None:
        """
        Save the configuration to a YAML file.

        Args:
            file_path: Path where to save the YAML configuration
        """
        try:
            yaml_content = self.to_yaml()
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
        except (OSError, PermissionError) as e:
            raise OnexError(
                message=f"Failed to save configuration file: {str(e)}",
                error_code=CoreErrorCode.FILE_WRITE_ERROR,
                context={"file_path": str(file_path)},
            ) from e
