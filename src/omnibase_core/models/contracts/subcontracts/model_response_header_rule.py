"""
Response Header Rule Model - ONEX Standards Compliant.

Strongly-typed model for response header transformation rules.
Replaces dict[str, str] with proper type safety.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import Field

from omnibase_core.enums.enum_response_header_transformation_type import (
    EnumResponseHeaderTransformationType,
)
from omnibase_core.models.contracts.subcontracts.model_base_header_transformation import (
    ModelBaseHeaderTransformation,
)


class ModelResponseHeaderRule(ModelBaseHeaderTransformation):
    """
    Strongly-typed response header transformation rule.

    Defines transformations for HTTP response headers with proper
    validation and type safety.

    Inherits common transformation fields from ModelBaseHeaderTransformation:
    - transformation_rule
    - apply_condition
    - case_sensitive
    - priority
    """

    header_name: str = Field(
        ...,
        description="Name of the response header to transform",
        min_length=1,
    )

    transformation_type: EnumResponseHeaderTransformationType = Field(
        default=EnumResponseHeaderTransformationType.SET,
        description="Type of transformation (set, append, prefix, suffix, remove, filter)",
    )

    expose_to_client: bool = Field(
        default=True,
        description="Whether to expose this header to the client",
    )

    cache_control_aware: bool = Field(
        default=False,
        description="Whether to consider cache-control headers when applying transformation",
    )
