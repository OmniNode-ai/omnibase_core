"""Rule Condition Model.

Rule condition with key-value pairs for matching.
"""

from pydantic import BaseModel, Field

from .model_rule_condition_value import ModelRuleConditionValue


class ModelRuleCondition(BaseModel):
    """Rule condition with key-value pairs for matching."""

    # Common condition fields
    operation_type: str | None = Field(None, description="Operation type to match")
    security_level: str | None = Field(None, description="Security level to match")
    environment: str | None = Field(None, description="Environment to match")

    # Complex conditions with operators
    operation_type_condition: ModelRuleConditionValue | None = Field(
        None,
        description="Operation type condition with operators",
    )
    security_level_condition: ModelRuleConditionValue | None = Field(
        None,
        description="Security level condition with operators",
    )

    # Additional fields can be added as needed
    source_node_id: str | None = Field(None, description="Source node ID to match")
    destination: str | None = Field(None, description="Destination to match")
    hop_count: int | None = Field(None, description="Hop count to match")
    is_encrypted: bool | None = Field(None, description="Encryption status to match")
    signature_count: int | None = Field(None, description="Signature count to match")
