"""
Event Mapping Rule Model - ONEX Standards Compliant.

Strongly-typed model for event field mapping rules.
Replaces dict[str, str] with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelEventMappingRule(BaseModel):
    """
    Strongly-typed event field mapping rule.

    Defines transformations for event fields with proper validation
    and type safety.
    """

    source_field: str = Field(
        ...,
        description="Source field name in the event",
        min_length=1,
    )

    target_field: str = Field(
        ...,
        description="Target field name after transformation",
        min_length=1,
    )

    mapping_type: str = Field(
        default="direct",
        description="Type of mapping (direct, transform, conditional, composite)",
    )

    transformation_expression: str | None = Field(
        default=None,
        description="Expression or template for field transformation",
    )

    default_value: str | None = Field(
        default=None,
        description="Default value if source field is missing",
    )

    is_required: bool = Field(
        default=False,
        description="Whether this mapping is required for the transformation",
    )

    apply_condition: str | None = Field(
        default=None,
        description="Condition for applying this mapping rule",
    )

    priority: int = Field(
        default=100,
        description="Priority of this mapping (higher values take precedence)",
        ge=0,
        le=1000,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
