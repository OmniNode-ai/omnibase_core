"""
Transformation Action Payload Model.

Payload for transformation actions (transform, convert, parse, etc.).
"""

from typing import List, Optional

from pydantic import Field, field_validator

from omnibase_core.model.core.model_action_payload_base import \
    ModelActionPayloadBase
from omnibase_core.model.core.model_node_action_type import ModelNodeActionType


class ModelTransformationActionPayload(ModelActionPayloadBase):
    """Payload for transformation actions (transform, convert, parse, etc.)."""

    input_format: Optional[str] = Field(
        None, description="Input format for transformation"
    )
    output_format: Optional[str] = Field(
        None, description="Output format for transformation"
    )
    transformation_rules: List[str] = Field(
        default_factory=list, description="Transformation rules to apply"
    )
    preserve_metadata: bool = Field(
        default=True, description="Whether to preserve metadata during transformation"
    )

    @field_validator("action_type")
    @classmethod
    def validate_transformation_action(
        cls, v: ModelNodeActionType
    ) -> ModelNodeActionType:
        """Validate that action_type is a valid transformation action."""
        from omnibase_core.model.core.predefined_categories import \
            TRANSFORMATION

        if v.category != TRANSFORMATION:
            raise ValueError(f"Invalid transformation action: {v.name}")
        return v
