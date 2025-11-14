"""
Header Transformation Model - ONEX Standards Compliant.

Strongly-typed model for HTTP header transformation rules.
Replaces dict[str, str] with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import Field

from omnibase_core.enums.enum_header_transformation_type import (
    EnumHeaderTransformationType,
)
from omnibase_core.models.contracts.subcontracts.model_base_header_transformation import (
    ModelBaseHeaderTransformation,
)


class ModelHeaderTransformation(ModelBaseHeaderTransformation):
    """
    Strongly-typed HTTP header transformation rule.

    Defines transformations for HTTP headers with proper validation
    and type safety.

    Inherits common transformation fields from ModelBaseHeaderTransformation:
    - transformation_rule
    - apply_condition
    - case_sensitive
    - priority
    """

    header_name: str = Field(
        ...,
        description="Name of the header to transform",
        min_length=1,
    )

    transformation_type: EnumHeaderTransformationType = Field(
        default=EnumHeaderTransformationType.SET,
        description="Type of transformation (set, append, prefix, suffix, remove)",
    )
