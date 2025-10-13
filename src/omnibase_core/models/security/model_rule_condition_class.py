"""Rule Condition Model.

Rule condition with key-value pairs for matching.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from .model_rule_condition_value import ModelRuleConditionValue


class ModelRuleCondition(BaseModel):
    """Rule condition with key-value pairs for matching."""

    # Common condition fields
    operation_type: str | None = Field(
        default=None, description="Operation type to match"
    )
    security_level: str | None = Field(
        default=None, description="Security level to match"
    )
    environment: str | None = Field(default=None, description="Environment to match")

    # Complex conditions with operators
    operation_type_condition: ModelRuleConditionValue | None = Field(
        default=None,
        description="Operation type condition with operators",
    )
    security_level_condition: ModelRuleConditionValue | None = Field(
        default=None,
        description="Security level condition with operators",
    )

    # Additional fields can be added as needed
    source_node_id: UUID | None = Field(
        default=None, description="Source node ID to match"
    )
    destination: str | None = Field(default=None, description="Destination to match")
    hop_count: int | None = Field(default=None, description="Hop count to match")
    is_encrypted: bool | None = Field(
        default=None, description="Encryption status to match"
    )
    signature_count: int | None = Field(
        default=None, description="Signature count to match"
    )
