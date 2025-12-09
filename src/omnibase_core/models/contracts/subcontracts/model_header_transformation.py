"""
Header Transformation Model.

Strongly-typed model for HTTP header transformation rules.
Replaces dict[str, str] with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import Field

from omnibase_core.enums.enum_header_transformation_type import (
    EnumHeaderTransformationType,
)
from omnibase_core.models.contracts.subcontracts.model_base_header_transformation import (
    ModelBaseHeaderTransformation,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


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

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    header_name: str = Field(
        ...,
        description="Name of the header to transform",
        min_length=1,
    )

    transformation_type: EnumHeaderTransformationType = Field(
        default=EnumHeaderTransformationType.SET,
        description="Type of transformation (set, append, prefix, suffix, remove)",
    )
