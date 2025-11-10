"""
Header Transformation Model - ONEX Standards Compliant.

Strongly-typed model for HTTP header transformation rules.
Replaces dict[str, str] with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelHeaderTransformation(BaseModel):
    """
    Strongly-typed HTTP header transformation rule.

    Defines transformations for HTTP headers with proper validation
    and type safety.
    """

    header_name: str = Field(
        ...,
        description="Name of the header to transform",
        min_length=1,
    )

    transformation_rule: str = Field(
        ...,
        description="Transformation rule or template for the header value",
        min_length=1,
    )

    transformation_type: str = Field(
        default="set",
        description="Type of transformation (set, append, prefix, suffix, remove)",
    )

    apply_condition: str | None = Field(
        default=None,
        description="Condition for applying this transformation",
    )

    case_sensitive: bool = Field(
        default=True,
        description="Whether header name matching is case-sensitive",
    )

    priority: int = Field(
        default=100,
        description="Priority of this transformation (higher values take precedence)",
        ge=0,
        le=1000,
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
