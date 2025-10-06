from typing import Any, Dict

from pydantic import Field

"""
Model for representing advanced parameters with proper type safety.

This model replaces dict[str, Any]ionary usage in CLI tool execution by providing
a structured representation of advanced parameters.
"""

from pydantic import BaseModel, Field


class ModelAdvancedParams(BaseModel):
    """
    Type-safe representation of advanced parameters for CLI tool execution.

    This model provides structured fields for common advanced parameters
    while maintaining flexibility through typed dict[str, Any]ionaries.
    """

    # Common advanced parameters
    parallel_execution: bool | None = Field(
        default=None,
        description="Enable parallel execution",
    )
    max_workers: int | None = Field(
        default=None,
        description="Maximum number of parallel workers",
    )
    retry_count: int | None = Field(
        default=None, description="Number of retry attempts"
    )
    retry_delay: float | None = Field(
        default=None,
        description="Delay between retries in seconds",
    )

    # Resource limits
    memory_limit_mb: int | None = Field(
        default=None,
        description="Memory limit in megabytes",
    )
    cpu_limit: float | None = Field(
        default=None,
        description="CPU limit as fraction (0.5 = 50%)",
    )
    time_limit_seconds: float | None = Field(
        default=None,
        description="Time limit for execution in seconds",
    )

    # Debugging and logging
    debug_mode: bool | None = Field(default=None, description="Enable debug mode")
    log_level: str | None = Field(
        default=None,
        description="Log level (DEBUG, INFO, WARNING, ERROR)",
    )
    trace_enabled: bool | None = Field(
        default=None, description="Enable execution tracing"
    )

    # Environment and context
    environment_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set",
    )
    working_directory: str | None = Field(
        default=None, description="Working directory path"
    )

    # Feature flags
    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flags for enabling/disabling features",
    )

    # Configuration overrides
    config_overrides: dict[str, str | int | float | bool] = Field(
        default_factory=dict,
        description="Configuration value overrides",
    )

    # Tool-specific string parameters
    string_params: dict[str, str] = Field(
        default_factory=dict,
        description="Tool-specific string parameters",
    )

    # Tool-specific numeric parameters
    numeric_params: dict[str, int | float] = Field(
        default_factory=dict,
        description="Tool-specific numeric parameters",
    )

    # Tool-specific list[Any]parameters
    list_params: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Tool-specific list[Any]parameters",
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dict[str, Any]ionary format for current standards.

        Returns:
            Dictionary representation of advanced parameters
        """
        # Custom reconstruction logic for advanced parameters format
        result = {}

        # Add non-None simple fields
        for field_name in [
            "parallel_execution",
            "max_workers",
            "retry_count",
            "retry_delay",
            "memory_limit_mb",
            "cpu_limit",
            "time_limit_seconds",
            "debug_mode",
            "log_level",
            "trace_enabled",
            "working_directory",
        ]:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value

        # Add non-empty dict[str, Any]ionaries
        if self.environment_vars:
            result["environment_vars"] = self.environment_vars
        if self.feature_flags:
            result["feature_flags"] = self.feature_flags
        if self.config_overrides:
            result["config_overrides"] = self.config_overrides
        if self.string_params:
            result.update(self.string_params)
        if self.numeric_params:
            result.update(self.numeric_params)
        if self.list_params:
            result.update(self.list_params)

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelAdvancedParams":
        """
        Create from dict[str, Any]ionary, intelligently categorizing parameters.

        Args:
            data: Dictionary of parameters

        Returns:
            ModelAdvancedParams instance
        """
        # Known field mappings
        known_fields = {
            "parallel_execution",
            "max_workers",
            "retry_count",
            "retry_delay",
            "memory_limit_mb",
            "cpu_limit",
            "time_limit_seconds",
            "debug_mode",
            "log_level",
            "trace_enabled",
            "working_directory",
            "environment_vars",
            "feature_flags",
            "config_overrides",
        }

        # Extract known fields
        kwargs = {}
        remaining = {}

        for key, value in data.items():
            if key in known_fields:
                kwargs[key] = value
            else:
                remaining[key] = value

        # Categorize remaining parameters by type
        string_params = {}
        numeric_params = {}
        list_params = {}

        for key, value in remaining.items():
            if isinstance(value, str):
                string_params[key] = value
            elif isinstance(value, int | float):
                numeric_params[key] = value
            elif isinstance(value, list) and all(
                isinstance(item, str) for item in value
            ):
                list_params[key] = value
            # Skip complex types that don't fit our categories

        kwargs["string_params"] = string_params
        kwargs["numeric_params"] = numeric_params
        kwargs["list_params"] = list_params

        return cls(**kwargs)
