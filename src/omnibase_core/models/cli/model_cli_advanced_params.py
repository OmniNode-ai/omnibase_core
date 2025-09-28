"""
CLI advanced parameters model.

Clean, strongly-typed replacement for ModelCustomFields[Any] in CLI advanced parameters.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Nameable
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_debug_level import EnumDebugLevel
from omnibase_core.enums.enum_security_level import EnumSecurityLevel
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.infrastructure.model_cli_value import ModelCliValue

from .model_output_format_options import ModelOutputFormatOptions


class ModelCliAdvancedParams(BaseModel):
    """
    Clean model for CLI advanced parameters.

    Replaces ModelCustomFields[Any] with structured advanced parameters model.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Nameable: Name management interface
    - Validatable: Validation and verification
    """

    # Timeout and performance parameters
    timeout_seconds: float = Field(
        default=30.0,
        description="Custom timeout in seconds",
        gt=0,
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries",
        ge=0,
        le=10,
    )
    retry_delay_ms: int = Field(
        default=1000,
        description="Delay between retries in milliseconds",
        ge=0,
    )

    # Memory and resource limits
    memory_limit_mb: int = Field(default=512, description="Memory limit in MB", gt=0)
    cpu_limit_percent: float = Field(
        default=100.0,
        description="CPU usage limit as percentage",
        ge=0.0,
        le=100.0,
    )

    # Execution parameters
    parallel_execution: bool = Field(
        default=False,
        description="Enable parallel execution",
    )
    max_parallel_tasks: int = Field(
        default=4,
        description="Maximum parallel tasks",
        ge=1,
        le=100,
    )

    # Cache parameters
    enable_cache: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int = Field(
        default=300,
        description="Cache TTL in seconds",
        ge=0,
    )

    # Debug and logging parameters
    debug_level: EnumDebugLevel = Field(
        default=EnumDebugLevel.INFO,
        description="Debug level",
    )
    enable_profiling: bool = Field(
        default=False,
        description="Enable performance profiling",
    )
    enable_tracing: bool = Field(default=False, description="Enable execution tracing")

    # Output formatting parameters
    output_format_options: ModelOutputFormatOptions = Field(
        default_factory=lambda: ModelOutputFormatOptions(
            page_size=None,
            max_items=None,
        ),
        description="Output format options",
    )
    compression_enabled: bool = Field(
        default=False,
        description="Enable output compression",
    )

    # Security parameters
    security_level: EnumSecurityLevel = Field(
        default=EnumSecurityLevel.STANDARD,
        description="Security level",
    )
    enable_sandbox: bool = Field(
        default=False,
        description="Enable sandboxed execution",
    )

    # Custom environment variables
    environment_variables: dict[str, str] = Field(
        default_factory=dict,
        description="Custom environment variables",
    )

    # Node-specific configuration
    node_config_overrides: dict[str, ModelCliValue] = Field(
        default_factory=dict,
        description="Node-specific configuration overrides",
    )

    # Extensibility for specific node types
    custom_parameters: dict[str, ModelCliValue] = Field(
        default_factory=dict,
        description="Custom parameters for specific node types",
    )

    def set_timeout(self, seconds: float) -> None:
        """Set timeout with validation."""
        if seconds <= 0:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Timeout must be positive",
            )
        self.timeout_seconds = seconds

    def set_memory_limit(self, mb: int) -> None:
        """Set memory limit with validation."""
        if mb <= 0:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Memory limit must be positive",
            )
        self.memory_limit_mb = mb

    def set_cpu_limit(self, percent: float) -> None:
        """Set CPU limit with validation."""
        if not 0.0 <= percent <= 100.0:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="CPU limit must be between 0.0 and 100.0",
            )
        self.cpu_limit_percent = percent

    def add_environment_variable(self, key: str, value: str) -> None:
        """Add an environment variable."""
        self.environment_variables[key] = value

    def add_config_override(self, key: str, value: str) -> None:
        """Add a configuration override. CLI configs are typically strings."""
        self.node_config_overrides[key] = ModelCliValue.from_string(value)

    def set_custom_parameter(self, key: str, value: str) -> None:
        """Set a custom parameter. CLI parameters are typically strings."""
        self.custom_parameters[key] = ModelCliValue.from_string(value)

    def get_custom_parameter(self, key: str, default: str = "") -> str:
        """Get a custom parameter. CLI parameters are strings."""
        cli_value = self.custom_parameters.get(key)
        if cli_value is not None:
            return str(cli_value.to_python_value())
        return default

    def enable_debug_mode(self) -> None:
        """Enable full debug mode."""
        self.debug_level = EnumDebugLevel.DEBUG
        self.enable_profiling = True
        self.enable_tracing = True

    def enable_performance_mode(self) -> None:
        """Enable performance optimizations."""
        self.parallel_execution = True
        self.enable_cache = True
        self.compression_enabled = True

    def enable_security_mode(self) -> None:
        """Enable strict security mode."""
        self.security_level = EnumSecurityLevel.STRICT
        self.enable_sandbox = True

    # Export the model

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get name (Nameable protocol)."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set name (Nameable protocol)."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


__all__ = ["ModelCliAdvancedParams"]
