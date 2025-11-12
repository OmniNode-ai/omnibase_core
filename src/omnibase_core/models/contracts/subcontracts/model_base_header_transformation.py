"""
Base Header Transformation Model - ONEX Standards Compliant.

Abstract base class for all header/parameter transformation rules.
Provides common fields and behavior to reduce duplication.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field


class ModelBaseHeaderTransformation(BaseModel):
    """
    Abstract base class for transformation rules.

    Provides common fields and validation logic shared across:
    - ModelHeaderTransformation (request headers)
    - ModelResponseHeaderRule (response headers)
    - ModelQueryParameterRule (query parameters)

    Subclasses must define:
    - name field (header_name or parameter_name)
    - transformation_type field (with specific enum type)
    - any additional unique fields
    """

    transformation_rule: str = Field(
        ...,
        description="Transformation rule or template for the value",
        min_length=1,
    )

    apply_condition: str | None = Field(
        default=None,
        description="Condition for applying this transformation",
    )

    case_sensitive: bool = Field(
        default=True,
        description="Whether name matching is case-sensitive",
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
