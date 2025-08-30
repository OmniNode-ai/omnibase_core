"""
ModelRuleCondition: Condition structure for policy rules.

This model defines conditions that trigger policy rules with proper typing.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelRuleConditionValue(BaseModel):
    """Value structure for rule conditions supporting various comparison types."""

    # Comparison operators
    in_values: Optional[List[str]] = Field(
        None, alias="$in", description="Values to match against"
    )
    regex: Optional[str] = Field(
        None, alias="$regex", description="Regular expression pattern"
    )
    gte: Optional[int] = Field(
        None, alias="$gte", description="Greater than or equal to value"
    )
    lte: Optional[int] = Field(
        None, alias="$lte", description="Less than or equal to value"
    )

    class Config:
        populate_by_name = True


class ModelRuleCondition(BaseModel):
    """Rule condition with key-value pairs for matching."""

    # Common condition fields
    operation_type: Optional[str] = Field(None, description="Operation type to match")
    security_level: Optional[str] = Field(None, description="Security level to match")
    environment: Optional[str] = Field(None, description="Environment to match")

    # Complex conditions with operators
    operation_type_condition: Optional[ModelRuleConditionValue] = Field(
        None, description="Operation type condition with operators"
    )
    security_level_condition: Optional[ModelRuleConditionValue] = Field(
        None, description="Security level condition with operators"
    )

    # Additional fields can be added as needed
    source_node_id: Optional[str] = Field(None, description="Source node ID to match")
    destination: Optional[str] = Field(None, description="Destination to match")
    hop_count: Optional[int] = Field(None, description="Hop count to match")
    is_encrypted: Optional[bool] = Field(None, description="Encryption status to match")
    signature_count: Optional[int] = Field(None, description="Signature count to match")
