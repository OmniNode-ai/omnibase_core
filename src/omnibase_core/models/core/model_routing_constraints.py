"""
ModelRoutingConstraints: Routing constraints and preferences.

This model defines constraints for event routing in the distributed system.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelRoutingConstraints(BaseModel):
    """Routing constraints and preferences."""

    max_latency_ms: int | None = Field(
        default=None, description="Maximum acceptable latency in milliseconds"
    )
    allowed_regions: list[str] = Field(
        default_factory=list, description="Allowed regions for routing"
    )
    min_security_level: str | None = Field(
        default=None, description="Minimum security level required"
    )
    custom_constraints: dict[str, ModelSchemaValue] = Field(
        default_factory=dict, description="Additional custom constraints"
    )


__all__ = ["ModelRoutingConstraints"]
