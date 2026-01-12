"""
Event Transformation Model.

Model for event transformation specifications in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_event_mapping_rule import ModelEventMappingRule


class ModelEventTransformation(BaseModel):
    """
    Event transformation specification.

    Defines transformation rules for event data,
    including filtering, mapping, and enrichment logic.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (auto-generated if not provided)",
    )

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

    mapping_rules: list[ModelEventMappingRule] = Field(
        default_factory=list,
        description="Strongly-typed field mapping rules for transformation",
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
