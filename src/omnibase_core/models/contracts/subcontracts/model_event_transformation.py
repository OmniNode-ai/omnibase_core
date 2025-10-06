from typing import Any

from pydantic import Field

"""
Event Transformation Model - ONEX Standards Compliant.

Model for event transformation specifications in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel, Field


class ModelEventTransformation(BaseModel):
    """
    Event transformation specification.

    Defines transformation rules for event data,
    including filtering, mapping, and enrichment logic.
    """

    transformation_name: str = Field(
        default=...,
        description="Unique name for the transformation",
        min_length=1,
    )

    transformation_type: str = Field(
        default=...,
        description="Type of transformation (filter, map, enrich, validate)",
        min_length=1,
    )

    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions for applying transformation",
    )

    mapping_rules: dict[str, str] = Field(
        default_factory=dict,
        description="Field mapping rules for transformation",
    )

    enrichment_sources: list[str] = Field(
        default_factory=list,
        description="External sources for event enrichment",
    )

    validation_schema: str | None = Field(
        default=None,
        description="Schema for event validation after transformation",
    )

    execution_order: int = Field(
        default=1,
        description="Order of transformation execution",
        ge=1,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
