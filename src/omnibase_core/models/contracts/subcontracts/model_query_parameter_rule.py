"""
Query Parameter Rule Model - ONEX Standards Compliant.

Strongly-typed model for query parameter transformation rules.
Replaces dict[str, str] with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelQueryParameterRule(BaseModel):
    """
    Strongly-typed query parameter transformation rule.

    Defines transformations for URL query parameters with proper
    validation and type safety.
    """

    parameter_name: str = Field(
        ...,
        description="Name of the query parameter to transform",
        min_length=1,
    )

    transformation_rule: str = Field(
        ...,
        description="Transformation rule or template for the parameter value",
        min_length=1,
    )

    transformation_type: str = Field(
        default="set",
        description="Type of transformation (set, append, prefix, suffix, remove, encode)",
    )

    apply_condition: str | None = Field(
        default=None,
        description="Condition for applying this transformation",
    )

    case_sensitive: bool = Field(
        default=True,
        description="Whether parameter name matching is case-sensitive",
    )

    url_encode: bool = Field(
        default=True,
        description="Whether to URL-encode the transformed value",
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
