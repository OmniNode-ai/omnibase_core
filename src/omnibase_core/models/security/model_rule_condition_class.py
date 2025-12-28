"""Rule Condition Model.

Rule condition with key-value pairs for matching policy contexts.

This module provides ModelRuleCondition, which defines the conditions that
must be met for a policy rule to apply. It supports both exact matching
and operator-based matching for flexible condition evaluation.

Example:
    >>> from omnibase_core.models.security.model_rule_condition_class import (
    ...     ModelRuleCondition,
    ... )
    >>> from omnibase_core.models.security.model_rule_condition_value import (
    ...     ModelRuleConditionValue,
    ... )
    >>> # Simple exact match condition
    >>> condition = ModelRuleCondition(
    ...     environment="production",
    ...     security_level="high",
    ... )
    >>> # Complex operator-based condition
    >>> condition = ModelRuleCondition(
    ...     operation_type_condition=ModelRuleConditionValue(
    ...         in_values=["create", "update", "delete"],
    ...     ),
    ...     hop_count_condition=ModelRuleConditionValue(gte=1, lte=5),
    ... )
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .model_rule_condition_value import ModelRuleConditionValue


class ModelRuleCondition(BaseModel):
    """Rule condition with key-value pairs for matching policy contexts.

    Represents conditions that determine whether a policy rule should apply
    to a given execution context. Supports two matching modes:

    1. **Exact Match**: Direct field comparison (e.g., environment="production")
    2. **Operator-Based**: Using ModelRuleConditionValue for complex matching:
       - $in: Value must be in a list of allowed values
       - $regex: Value must match a regular expression
       - $gte/$lte: Numeric greater-than-or-equal / less-than-or-equal

    Attributes:
        operation_type: Exact operation type string to match.
        security_level: Exact security level string to match.
        environment: Exact environment string to match (e.g., "production",
            "development", "staging").
        operation_type_condition: Operator-based condition for operation type
            matching. Supports $in for list membership and $regex for pattern
            matching.
        security_level_condition: Operator-based condition for security level
            matching. Supports $in and $regex operators.
        hop_count_condition: Operator-based condition for hop count matching.
            Supports $gte (minimum) and $lte (maximum) for range validation.
        source_node_id: Exact UUID of the source node to match.
        destination: Exact destination string to match.
        hop_count: Exact hop count integer to match.
        is_encrypted: Exact encryption status boolean to match.
        signature_count: Exact signature count integer to match.

    Example:
        >>> # Match production environment with high security
        >>> condition = ModelRuleCondition(
        ...     environment="production",
        ...     security_level="high",
        ... )

        >>> # Match any sensitive operation with 1-5 hops
        >>> from omnibase_core.models.security.model_rule_condition_value import (
        ...     ModelRuleConditionValue,
        ... )
        >>> condition = ModelRuleCondition(
        ...     operation_type_condition=ModelRuleConditionValue(
        ...         in_values=["create_user", "delete_user", "modify_permissions"],
        ...     ),
        ...     hop_count_condition=ModelRuleConditionValue(gte=1, lte=5),
        ...     is_encrypted=True,
        ... )

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

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
        description="Operation type condition with operators (supports $in, $regex)",
    )
    security_level_condition: ModelRuleConditionValue | None = Field(
        default=None,
        description="Security level condition with operators (supports $in, $regex for string matching)",
    )
    hop_count_condition: ModelRuleConditionValue | None = Field(
        default=None,
        description="Hop count condition with operators (supports $gte, $lte for numeric comparison)",
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
