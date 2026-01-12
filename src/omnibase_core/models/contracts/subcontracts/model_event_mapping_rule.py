"""
Event Mapping Rule Model.

Strongly-typed model for event field mapping rules.
Replaces dict[str, str] with proper type safety.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_mapping_type import EnumMappingType
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEventMappingRule(BaseModel):
    """
    Strongly-typed event field mapping rule.

    Defines transformations for event fields with proper validation
    and type safety.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Subcontract version (auto-generated if not provided)",
    )

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

    mapping_type: EnumMappingType = Field(
        default=EnumMappingType.DIRECT,
        description="Type of mapping (direct, transform, conditional, composite)",
    )

    transformation_expression: str | None = Field(
        default=None,
        description="Expression or template for field transformation",
    )

    default_value: str | int | float | bool | None = Field(
        default=None,
        description=(
            "Default value if source field is missing. "
            "Supports str, int, float, bool, or None types."
        ),
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
