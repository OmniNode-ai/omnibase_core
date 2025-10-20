"""
Execution Metadata Model.

Metadata for execution contexts including timeouts,
retry policies, and debugging configuration.
"""

from pydantic import Field

from omnibase_core.enums.enum_debug_level import EnumDebugLevel
from omnibase_core.models.configuration.model_retry_policy import ModelRetryPolicy
from omnibase_core.models.core.model_duration import ModelDuration

from .model_metadata_base import ModelMetadataBase


class ModelExecutionMetadata(ModelMetadataBase):
    """
    Metadata for execution contexts.

    Extends base metadata with execution-specific information like
    timeouts, retry policies, and debugging configuration.
    """

    timeout: ModelDuration = Field(
        default_factory=lambda: ModelDuration(milliseconds=30000),
        description="Execution timeout",
    )
    retry_policy: ModelRetryPolicy | None = Field(
        default=None,
        description="Retry policy for failures",
    )
    trace_enabled: bool = Field(default=False, description="Enable execution tracing")
    debug_level: EnumDebugLevel | None = Field(
        default=None,
        description="Debug verbosity level",
    )
    profiling_enabled: bool = Field(
        default=False,
        description="Enable performance profiling",
    )
    metrics_collection: bool = Field(
        default=True,
        description="Enable metrics collection",
    )

    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.debug_level is not None or self.trace_enabled

    def should_collect_metrics(self) -> bool:
        """Check if metrics should be collected."""
        return self.metrics_collection or self.profiling_enabled
