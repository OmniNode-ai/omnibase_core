"""
Node configuration summary model.

Clean, strongly-typed replacement for node configuration dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelNodeConfigurationSummary(BaseModel):
    """Node configuration summary with specific types."""

    execution: dict[str, str | int | float | bool | None] = Field(
        description="Execution configuration summary"
    )
    resources: dict[str, str | int | float | bool | None] = Field(
        description="Resource configuration summary"
    )
    features: dict[str, str | int | float | bool | None] = Field(
        description="Feature configuration summary"
    )
    connection: dict[str, str | int | float | bool | None] = Field(
        description="Connection configuration summary"
    )
    is_production_ready: bool = Field(
        description="Whether configuration is production ready"
    )
    is_performance_optimized: bool = Field(
        description="Whether configuration is performance optimized"
    )
    has_custom_settings: bool = Field(
        description="Whether configuration has custom settings"
    )


# Export the model
__all__ = ["ModelNodeConfigurationSummary"]
