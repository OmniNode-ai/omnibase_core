"""Policy Rule Model.

Individual policy rule with conditions and actions for trust policy evaluation.

This module provides ModelPolicyRule, which defines individual rules within a
ModelTrustPolicy. Each rule specifies conditions that must be matched and
security requirements (signatures, algorithms, compliance) that must be met.

This module was extracted from model_trustpolicy.py to resolve circular import
issues while maintaining clean separation of concerns.

Example:
    >>> from omnibase_core.models.security.model_policy_rule import ModelPolicyRule
    >>> from omnibase_core.models.security.model_rule_condition import ModelRuleCondition
    >>> rule = ModelPolicyRule(
    ...     name="Production Security",
    ...     conditions=ModelRuleCondition(environment="production"),
    ...     minimum_signatures=2,
    ...     required_algorithms=["RS256", "ES256"],
    ... )
    >>> rule.is_active()
    True
"""

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .model_policy_severity import ModelPolicySeverity
from .model_rule_condition import ModelRuleCondition


class ModelPolicyRule(BaseModel):
    """Individual policy rule with conditions and actions.

    Represents a single rule within a trust policy that defines when the rule
    applies (via conditions) and what security requirements must be enforced
    when it matches (signatures, algorithms, trusted nodes, etc.).

    Rules are evaluated in order within a ModelTrustPolicy, with later rules
    potentially overriding or augmenting requirements from earlier rules.

    Attributes:
        rule_id: Unique identifier for this rule (auto-generated UUID).
        name: Human-readable name for the rule (required).
        description: Optional detailed description of the rule's purpose.
        conditions: ModelRuleCondition defining when this rule applies.
        require_signatures: Whether cryptographic signatures are required.
        minimum_signatures: Minimum number of valid signatures needed.
        required_algorithms: List of acceptable signature algorithms
            (e.g., ["RS256", "ES256"]).
        trusted_nodes: Set of node identifiers trusted under this rule.
        compliance_tags: Compliance framework tags this rule enforces
            (e.g., ["SOX", "HIPAA"]).
        audit_level: Detail level for audit logging ("minimal", "standard",
            "detailed").
        violation_severity: Severity configuration for rule violations.
        allow_override: Whether manual override of violations is permitted.
        enabled: Whether the rule is currently active.
        valid_from: Optional datetime when rule becomes effective.
        valid_until: Optional datetime when rule expires.

    Example:
        >>> rule = ModelPolicyRule(
        ...     name="High Security Operations",
        ...     conditions=ModelRuleCondition(
        ...         operation_type="sensitive",
        ...         security_level="high",
        ...     ),
        ...     minimum_signatures=3,
        ...     required_algorithms=["ES256"],
        ...     compliance_tags=["SOX", "GDPR"],
        ... )
        >>> context = ModelRuleCondition(
        ...     operation_type="sensitive",
        ...     security_level="high",
        ... )
        >>> rule.matches_condition(context)
        True

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    rule_id: UUID = Field(default_factory=uuid4, description="Unique rule identifier")
    name: str = Field(default=..., description="Human-readable rule name")
    description: str | None = Field(default=None, description="Rule description")
    conditions: ModelRuleCondition = Field(
        default_factory=lambda: ModelRuleCondition(),
        description="Conditions that trigger this rule",
    )
    require_signatures: bool = Field(default=True, description="Require signatures")
    minimum_signatures: int = Field(default=1, description="Minimum signature count")
    required_algorithms: list[str] = Field(
        default_factory=list, description="Required signature algorithms"
    )
    trusted_nodes: set[str] = Field(
        default_factory=set, description="Nodes trusted for this rule"
    )
    compliance_tags: list[str] = Field(
        default_factory=list, description="Required compliance tags"
    )
    audit_level: str = Field(default="standard", description="Audit detail level")
    violation_severity: ModelPolicySeverity = Field(
        default_factory=lambda: ModelPolicySeverity(),
        description="Severity of policy violations",
    )
    allow_override: bool = Field(
        default=False, description="Allow manual override of violations"
    )
    enabled: bool = Field(default=True, description="Whether rule is active")
    valid_from: datetime | None = Field(
        default=None, description="Rule effective start time"
    )
    valid_until: datetime | None = Field(
        default=None, description="Rule expiration time"
    )

    def is_active(self, check_time: datetime | None = None) -> bool:
        """Check if rule is currently active based on enabled status and time bounds.

        A rule is considered active if:
        1. The enabled flag is True
        2. The current time is after valid_from (if set)
        3. The current time is before valid_until (if set)

        Args:
            check_time: Optional datetime to check against. If None, uses
                the current UTC time.

        Returns:
            True if the rule is currently active and should be evaluated,
            False otherwise.

        Example:
            >>> from datetime import datetime, UTC, timedelta
            >>> rule = ModelPolicyRule(name="Test Rule")
            >>> rule.is_active()
            True
            >>> rule.enabled = False
            >>> rule.is_active()
            False
        """
        if not self.enabled:
            return False
        if check_time is None:
            check_time = datetime.now(UTC)
        if self.valid_from and check_time < self.valid_from:
            return False
        return not (self.valid_until and check_time > self.valid_until)

    def matches_condition(self, context: ModelRuleCondition) -> bool:
        """Check if the given context matches this rule's conditions.

        Evaluates all conditions defined in this rule against the provided
        context. All conditions must match for the rule to apply (AND logic).

        Supports multiple matching modes:
        - Exact match: Direct field comparison (operation_type, security_level)
        - Operator-based: Using ModelRuleConditionValue for $in, $regex, $gte, $lte
        - Numeric comparison: For hop_count using $gte and $lte operators

        Args:
            context: ModelRuleCondition containing the current execution context
                to evaluate against this rule's conditions.

        Returns:
            True if all conditions match the context, False if any condition
            fails to match.

        Example:
            >>> rule = ModelPolicyRule(
            ...     name="Production Rule",
            ...     conditions=ModelRuleCondition(environment="production"),
            ... )
            >>> context = ModelRuleCondition(environment="production")
            >>> rule.matches_condition(context)
            True
            >>> context = ModelRuleCondition(environment="development")
            >>> rule.matches_condition(context)
            False
        """
        if (
            self.conditions.operation_type
            and context.operation_type != self.conditions.operation_type
        ):
            return False
        if self.conditions.operation_type_condition:
            if (
                self.conditions.operation_type_condition.in_values
                and context.operation_type
                not in self.conditions.operation_type_condition.in_values
            ):
                return False
            if self.conditions.operation_type_condition.regex:
                if not re.match(
                    self.conditions.operation_type_condition.regex,
                    context.operation_type or "",
                ):
                    return False
        if (
            self.conditions.security_level
            and context.security_level != self.conditions.security_level
        ):
            return False
        if self.conditions.security_level_condition:
            # String-based security level matching using in_values and regex
            if (
                self.conditions.security_level_condition.in_values
                and context.security_level
                not in self.conditions.security_level_condition.in_values
            ):
                return False
            if self.conditions.security_level_condition.regex:
                if not re.match(
                    self.conditions.security_level_condition.regex,
                    context.security_level or "",
                ):
                    return False
        if self.conditions.hop_count_condition:
            # Numeric hop count matching using gte and lte
            if self.conditions.hop_count_condition.gte and (
                context.hop_count is None
                or context.hop_count < self.conditions.hop_count_condition.gte
            ):
                return False
            if self.conditions.hop_count_condition.lte and (
                context.hop_count is None
                or context.hop_count > self.conditions.hop_count_condition.lte
            ):
                return False
        if (
            self.conditions.environment
            and context.environment != self.conditions.environment
        ):
            return False
        if (
            self.conditions.source_node_id
            and context.source_node_id != self.conditions.source_node_id
        ):
            return False
        if (
            self.conditions.destination
            and context.destination != self.conditions.destination
        ):
            return False
        if (
            self.conditions.hop_count is not None
            and context.hop_count != self.conditions.hop_count
        ):
            return False
        if (
            self.conditions.is_encrypted is not None
            and context.is_encrypted != self.conditions.is_encrypted
        ):
            return False
        return not (
            self.conditions.signature_count is not None
            and context.signature_count != self.conditions.signature_count
        )
