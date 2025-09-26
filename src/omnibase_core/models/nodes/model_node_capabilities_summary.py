"""
Node capabilities summary model.

Clean, strongly-typed replacement for node capabilities dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelNodeCapabilitiesSummary(BaseModel):
    """Node capabilities summary with specific types."""

    capabilities_count: int = Field(description="Number of capabilities")
    operations_count: int = Field(description="Number of operations")
    dependencies_count: int = Field(description="Number of dependencies")
    has_capabilities: bool = Field(description="Whether node has capabilities")
    has_operations: bool = Field(description="Whether node has operations")
    has_dependencies: bool = Field(description="Whether node has dependencies")
    has_performance_metrics: bool = Field(
        description="Whether node has performance metrics",
    )
    primary_capability: str | None = Field(description="Primary capability if any")
    metrics_count: int = Field(description="Number of metrics")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelNodeCapabilitiesSummary"]
