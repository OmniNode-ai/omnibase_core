"""
Query Parameter Rule Model.

Strongly-typed model for query parameter transformation rules.
Replaces dict[str, str] with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import Field

from omnibase_core.enums.enum_query_parameter_transformation_type import (
    EnumQueryParameterTransformationType,
)
from omnibase_core.models.contracts.subcontracts.model_base_header_transformation import (
    ModelBaseHeaderTransformation,
)


class ModelQueryParameterRule(ModelBaseHeaderTransformation):
    """
    Strongly-typed query parameter transformation rule.

    Defines transformations for URL query parameters with proper
    validation and type safety.

    Inherits common transformation fields from ModelBaseHeaderTransformation:
    - version
    - transformation_rule
    - apply_condition
    - case_sensitive
    - priority
    """

    parameter_name: str = Field(
        ...,
        description="Name of the query parameter to transform",
        min_length=1,
    )

    transformation_type: EnumQueryParameterTransformationType = Field(
        default=EnumQueryParameterTransformationType.SET,
        description="Type of transformation (set, append, prefix, suffix, remove, encode)",
    )

    url_encode: bool = Field(
        default=True,
        description="Whether to URL-encode the transformed value",
    )
