from pydantic import Field

from .model_trustpolicy import ModelTrustPolicy

__all__ = [
    "ModelPolicyRule",
    "ModelTrustPolicy",
]

"\nModelTrustPolicy: Flexible trust policy engine for signature requirements.\n\nThis model defines trust policies that control signature requirements,\ncertificate validation, and compliance rules for secure envelope routing.\n"
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel

from .model_policy_severity import ModelPolicySeverity
from .model_rule_condition import ModelRuleCondition


class ModelPolicyRule(BaseModel):
    """Individual policy rule with conditions and actions."""

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
        """Check if rule is currently active."""
        if not self.enabled:
            return False
        if check_time is None:
            check_time = datetime.now(UTC)
        if self.valid_from and check_time < self.valid_from:
            return False
        return not (self.valid_until and check_time > self.valid_until)

    def matches_condition(self, context: ModelRuleCondition) -> bool:
        """Check if context matches rule conditions."""
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
                import re

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
            if self.conditions.security_level_condition.gte and (
                not context.hop_count
                or context.hop_count < self.conditions.security_level_condition.gte
            ):
                return False
            if self.conditions.security_level_condition.lte and (
                not context.hop_count
                or context.hop_count > self.conditions.security_level_condition.lte
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
