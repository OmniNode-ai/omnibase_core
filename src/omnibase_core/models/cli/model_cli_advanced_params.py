"""
CLI advanced parameters model.

Clean, strongly-typed replacement for ModelCustomFields[Any] in CLI advanced parameters.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...enums.enum_debug_level import EnumDebugLevel
from ...enums.enum_security_level import EnumSecurityLevel
from .model_output_format_options import ModelOutputFormatOptions


class ModelCliAdvancedParams(BaseModel):
    """
    Clean model for CLI advanced parameters.

    Replaces ModelCustomFields[Any] with structured advanced parameters model.
    """

    # Timeout and performance parameters
    timeout_seconds: float | None = Field(
        None, description="Custom timeout in seconds", gt=0
    )
    max_retries: int | None = Field(
        None, description="Maximum number of retries", ge=0, le=10
    )
    retry_delay_ms: int | None = Field(
        None, description="Delay between retries in milliseconds", ge=0
    )

    # Memory and resource limits
    memory_limit_mb: int | None = Field(None, description="Memory limit in MB", gt=0)
    cpu_limit_percent: float | None = Field(
        None, description="CPU usage limit as percentage", ge=0.0, le=100.0
    )

    # Execution parameters
    parallel_execution: bool = Field(
        default=False, description="Enable parallel execution"
    )
    max_parallel_tasks: int | None = Field(
        None, description="Maximum parallel tasks", ge=1, le=100
    )

    # Cache parameters
    enable_cache: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int | None = Field(
        None, description="Cache TTL in seconds", ge=0
    )

    # Debug and logging parameters
    debug_level: EnumDebugLevel = Field(
        default=EnumDebugLevel.INFO,
        description="Debug level",
    )
    enable_profiling: bool = Field(
        default=False, description="Enable performance profiling"
    )
    enable_tracing: bool = Field(default=False, description="Enable execution tracing")

    # Output formatting parameters
    output_format_options: ModelOutputFormatOptions = Field(
        default_factory=ModelOutputFormatOptions, description="Output format options"
    )
    compression_enabled: bool = Field(
        default=False, description="Enable output compression"
    )

    # Security parameters
    security_level: EnumSecurityLevel = Field(
        default=EnumSecurityLevel.STANDARD,
        description="Security level",
    )
    enable_sandbox: bool = Field(
        default=False, description="Enable sandboxed execution"
    )

    # Custom environment variables
    environment_variables: dict[str, str] = Field(
        default_factory=dict, description="Custom environment variables"
    )

    # Node-specific configuration
    node_config_overrides: dict[str, str | int | bool] = Field(
        default_factory=dict, description="Node-specific configuration overrides"
    )

    # Extensibility for specific node types
    custom_parameters: dict[str, str | int | bool | float] = Field(
        default_factory=dict, description="Custom parameters for specific node types"
    )

    def set_timeout(self, seconds: float) -> None:
        """Set timeout with validation."""
        if seconds <= 0:
            raise ValueError("Timeout must be positive")
        self.timeout_seconds = seconds

    def set_memory_limit(self, mb: int) -> None:
        """Set memory limit with validation."""
        if mb <= 0:
            raise ValueError("Memory limit must be positive")
        self.memory_limit_mb = mb

    def set_cpu_limit(self, percent: float) -> None:
        """Set CPU limit with validation."""
        if not 0.0 <= percent <= 100.0:
            raise ValueError("CPU limit must be between 0.0 and 100.0")
        self.cpu_limit_percent = percent

    def add_environment_variable(self, key: str, value: str) -> None:
        """Add an environment variable."""
        self.environment_variables[key] = value

    def add_config_override(self, key: str, value: str | int | bool) -> None:
        """Add a configuration override."""
        self.node_config_overrides[key] = value

    def set_custom_parameter(self, key: str, value: str | int | bool | float) -> None:
        """Set a custom parameter."""
        self.custom_parameters[key] = value

    def get_custom_parameter(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get a custom parameter."""
        return self.custom_parameters.get(key, default)

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
__all__ = ["ModelCliAdvancedParams"]
