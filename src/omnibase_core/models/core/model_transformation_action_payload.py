"""
Transformation Action Payload Model.

Payload for transformation actions (transform, convert, parse, etc.).
"""

from pydantic import Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelTransformationActionPayload(ModelActionPayloadBase):
    """Payload for transformation actions (transform, convert, parse, etc.)."""

    input_format: str | None = Field(
        default=None,
        description="Input format for transformation",
    )
    output_format: str | None = Field(
        default=None,
        description="Output format for transformation",
    )
    transformation_rules: list[str] = Field(
        default_factory=list,
        description="Transformation rules to apply",
    )
    preserve_metadata: bool = Field(
        default=True,
        description="Whether to preserve metadata during transformation",
    )

    @field_validator("action_type")
    @classmethod
    def validate_transformation_action(
        cls,
        v: ModelNodeActionType,
    ) -> ModelNodeActionType:
        """Validate that action_type is a valid transformation action."""
        from omnibase_core.models.core.model_predefined_categories import TRANSFORMATION

        if v.category != TRANSFORMATION:
            msg = f"Invalid transformation action: {v.name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v
