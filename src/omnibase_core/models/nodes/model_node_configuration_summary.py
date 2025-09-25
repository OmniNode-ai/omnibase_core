"""
Node configuration summary model.

Clean, strongly-typed replacement for node configuration dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue


class ModelNodeConfigurationSummary(BaseModel):
    """Node configuration summary with strongly-typed values."""

    # Execution config using typed metadata values
    execution: dict[str, ModelMetadataValue | None] = Field(
        description="Execution configuration summary with type-safe values",
    )

    # Resources using numeric values for consistency
    resources: dict[str, ModelNumericValue | None] = Field(
        description="Resource configuration summary with numeric values",
    )

    # Features simplified - use string list for feature flags
    features: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Feature configuration as string lists",
    )

    # Connection config using string values (most common for connection strings, hosts, etc.)
    connection: dict[str, str | None] = Field(
        description="Connection configuration summary (string values)",
    )
    is_production_ready: bool = Field(
        description="Whether configuration is production ready",
    )
    is_performance_optimized: bool = Field(
        description="Whether configuration is performance optimized",
    )
    has_custom_settings: bool = Field(
        description="Whether configuration has custom settings",
    )


# Export the model
__all__ = ["ModelNodeConfigurationSummary"]
