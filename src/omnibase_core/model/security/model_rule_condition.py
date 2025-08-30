"""
ModelRuleCondition: Condition structure for policy rules.

This model defines conditions that trigger policy rules with proper typing.
"""

from pydantic import BaseModel, Field


class ModelRuleConditionValue(BaseModel):
    """Value structure for rule conditions supporting various comparison types."""

    # Comparison operators
    in_values: list[str] | None = Field(
        None,
        alias="$in",
        description="Values to match against",
    )
    regex: str | None = Field(
        None,
        alias="$regex",
        description="Regular expression pattern",
    )
    gte: int | None = Field(
        None,
        alias="$gte",
        description="Greater than or equal to value",
    )
    lte: int | None = Field(
        None,
        alias="$lte",
        description="Less than or equal to value",
    )

    class Config:
        populate_by_name = True


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
