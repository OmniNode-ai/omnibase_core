"""
TypedDict for CLI advanced parameters serialization output.

Strongly-typed representation for ModelCliAdvancedParams.serialize() return value.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

# Use TYPE_CHECKING to avoid circular import
if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_model_value_serialized import (
        TypedDictModelValueSerialized,
    )
    from omnibase_core.types.typed_dict_output_format_options_serialized import (
        TypedDictOutputFormatOptionsSerialized,
    )


class TypedDictCliAdvancedParamsSerialized(TypedDict):
    """
    Strongly-typed representation of ModelCliAdvancedParams.serialize() output.

    This replaces dict[str, Any] with proper type safety for serialization output.
    Follows ONEX strong typing principles by eliminating dict[str, Any] usage.
    """

    # Timeout and performance parameters
    timeout_seconds: float
    max_retries: int
    retry_delay_ms: int

    # Memory and resource limits
    memory_limit_mb: int
    cpu_limit_percent: float

    # Execution parameters
    parallel_execution: bool
    max_parallel_tasks: int

    # Cache parameters
    enable_cache: bool
    cache_ttl_seconds: int

    # Debug and logging parameters - enum serialized as string (use_enum_values=True)
    debug_level: str
    enable_profiling: bool
    enable_tracing: bool

    # Output formatting parameters
    output_format_options: TypedDictOutputFormatOptionsSerialized
    compression_enabled: bool

    # Security parameters - enum serialized as string (use_enum_values=True)
    security_level: str
    enable_sandbox: bool

    # Custom environment variables
    environment_variables: dict[str, str]

    # Node-specific configuration
    node_config_overrides: dict[str, TypedDictModelValueSerialized]

    # Extensibility for specific node types
    custom_parameters: dict[str, TypedDictModelValueSerialized]


# Export for use
__all__ = ["TypedDictCliAdvancedParamsSerialized"]
