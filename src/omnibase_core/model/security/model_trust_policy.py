"""
ModelTrustPolicy: Flexible trust policy engine for signature requirements.

This model defines trust policies that control signature requirements,
certificate validation, and compliance rules for secure envelope routing.
"""

from datetime import datetime, timedelta
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .model_certificate_validation_level import ModelCertificateValidationLevel
from .model_encryption_requirement import ModelEncryptionRequirement
from .model_policy_severity import ModelPolicySeverity
from .model_policy_validation_result import ModelPolicyValidationResult
from .model_rule_condition import ModelRuleCondition, ModelRuleConditionValue
from .model_signature_requirements import ModelSignatureRequirements
from .model_trust_level import ModelTrustLevel


class PolicyRule(BaseModel):
    """Individual policy rule with conditions and actions."""

    rule_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique rule identifier",
    )
    name: str = Field(..., description="Human-readable rule name")
    description: str | None = Field(None, description="Rule description")

    # Rule conditions
    conditions: ModelRuleCondition = Field(
        default_factory=ModelRuleCondition,
        description="Conditions that trigger this rule",
    )

    # Rule actions
    require_signatures: bool = Field(default=True, description="Require signatures")
    minimum_signatures: int = Field(default=1, description="Minimum signature count")
    required_algorithms: list[str] = Field(
        default_factory=list,
        description="Required signature algorithms",
    )
    trusted_nodes: set[str] = Field(
        default_factory=set,
        description="Nodes trusted for this rule",
    )

    # Compliance requirements
    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Required compliance tags",
    )
    audit_level: str = Field(default="standard", description="Audit detail level")

    # Violation handling
    violation_severity: ModelPolicySeverity = Field(
        default_factory=ModelPolicySeverity,
        description="Severity of policy violations",
    )
    allow_override: bool = Field(
        default=False,
        description="Allow manual override of violations",
    )

    # Rule lifecycle
    enabled: bool = Field(default=True, description="Whether rule is active")
    valid_from: datetime | None = Field(
        None,
        description="Rule effective start time",
    )
    valid_until: datetime | None = Field(None, description="Rule expiration time")

    def is_active(self, check_time: datetime | None = None) -> bool:
        """Check if rule is currently active."""
        if not self.enabled:
            return False

        if check_time is None:
            check_time = datetime.utcnow()

        if self.valid_from and check_time < self.valid_from:
            return False

        return not (self.valid_until and check_time > self.valid_until)

    def matches_condition(self, context: ModelRuleCondition) -> bool:
        """Check if context matches rule conditions."""
        # Check operation type
        if (
            self.conditions.operation_type
            and context.operation_type != self.conditions.operation_type
        ):
            return False

        # Check operation type with conditions
        if self.conditions.operation_type_condition:
            if self.conditions.operation_type_condition.in_values and (
                context.operation_type
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

        # Check security level
        if (
            self.conditions.security_level
            and context.security_level != self.conditions.security_level
        ):
            return False

        # Check security level with conditions
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

        # Check environment
        if (
            self.conditions.environment
            and context.environment != self.conditions.environment
        ):
            return False

        # Check other fields
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


class ModelTrustPolicy(BaseModel):
    """
    Trust policy engine for signature and compliance requirements.

    Defines flexible rules for signature requirements, certificate validation,
    and compliance enforcement across different security contexts.
    """

    # Policy identification
    policy_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique policy identifier",
    )
    name: str = Field(..., description="Policy name")
    version: str = Field(default="1.0", description="Policy version")
    description: str | None = Field(None, description="Policy description")

    # Policy metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When policy was created",
    )
    created_by: str = Field(..., description="Policy creator")
    organization: str | None = Field(None, description="Organization name")

    # Global policy settings
    default_trust_level: ModelTrustLevel = Field(
        default_factory=lambda: ModelTrustLevel(level="standard"),
        description="Default trust level for envelopes",
    )
    certificate_validation: ModelCertificateValidationLevel = Field(
        default_factory=lambda: ModelCertificateValidationLevel(level="standard"),
        description="Certificate validation level",
    )
    encryption_requirement: ModelEncryptionRequirement = Field(
        default_factory=lambda: ModelEncryptionRequirement(level="optional"),
        description="Payload encryption requirement",
    )

    # Signature requirements
    global_minimum_signatures: int = Field(
        default=1,
        description="Global minimum signature requirement",
    )
    maximum_signature_age_hours: int = Field(
        default=24,
        description="Maximum age of signatures in hours",
    )
    require_timestamp_verification: bool = Field(
        default=True,
        description="Require timestamp signature verification",
    )

    # Certificate and PKI settings
    trusted_certificate_authorities: list[str] = Field(
        default_factory=list,
        description="Trusted CA certificate fingerprints",
    )
    certificate_revocation_check: bool = Field(
        default=True,
        description="Enable certificate revocation checking",
    )
    require_certificate_transparency: bool = Field(
        default=False,
        description="Require certificates to be in CT logs",
    )

    # Node trust settings
    globally_trusted_nodes: set[str] = Field(
        default_factory=set,
        description="Globally trusted node IDs",
    )
    blocked_nodes: set[str] = Field(default_factory=set, description="Blocked node IDs")
    require_node_registration: bool = Field(
        default=True,
        description="Require nodes to be registered",
    )

    # Policy rules
    rules: list[PolicyRule] = Field(
        default_factory=list,
        description="Ordered list of policy rules",
    )

    # Compliance and audit
    compliance_frameworks: list[str] = Field(
        default_factory=list,
        description="Required compliance frameworks",
    )
    audit_retention_days: int = Field(
        default=2555,  # 7 years for SOX compliance
        description="Audit log retention period in days",
    )
    require_audit_trail: bool = Field(
        default=True,
        description="Require complete audit trail",
    )

    # Performance settings
    signature_timeout_ms: int = Field(
        default=15000,
        description="Maximum signature operation time in milliseconds",
    )
    verification_timeout_ms: int = Field(
        default=10000,
        description="Maximum verification time in milliseconds",
    )
    cache_verification_results: bool = Field(
        default=True,
        description="Cache signature verification results",
    )
    verification_cache_ttl_seconds: int = Field(
        default=3600,
        description="Verification cache TTL in seconds",
    )

    # Policy enforcement
    enforcement_mode: str = Field(
        default="strict",
        description="Enforcement mode: 'strict', 'permissive', 'monitor'",
    )
    allow_emergency_override: bool = Field(
        default=False,
        description="Allow emergency policy override",
    )
    emergency_override_roles: list[str] = Field(
        default_factory=list,
        description="Roles authorized for emergency override",
    )

    # Policy lifecycle
    effective_from: datetime = Field(
        default_factory=datetime.utcnow,
        description="When policy becomes effective",
    )
    expires_at: datetime | None = Field(None, description="When policy expires")
    auto_renewal: bool = Field(default=False, description="Automatically renew policy")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    @field_validator("global_minimum_signatures")
    @classmethod
    def validate_minimum_signatures(cls, v):
        """Validate minimum signature count."""
        if v < 0:
            msg = "Minimum signatures cannot be negative"
            raise ValueError(msg)
        if v > 100:
            msg = "Minimum signatures cannot exceed 100"
            raise ValueError(msg)
        return v

    @field_validator("enforcement_mode")
    @classmethod
    def validate_enforcement_mode(cls, v):
        """Validate enforcement mode."""
        valid_modes = ["strict", "permissive", "monitor"]
        if v not in valid_modes:
            msg = f"Invalid enforcement mode. Must be one of: {valid_modes}"
            raise ValueError(msg)
        return v

    def is_active(self, check_time: datetime | None = None) -> bool:
        """Check if policy is currently active."""
        if check_time is None:
            check_time = datetime.utcnow()

        if check_time < self.effective_from:
            return False

        return not (self.expires_at and check_time > self.expires_at)

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a new policy rule."""
        self.rules.append(rule)

    def get_applicable_rules(self, context: ModelRuleCondition) -> list[PolicyRule]:
        """Get rules that apply to the given context."""
        applicable_rules = []

        for rule in self.rules:
            if rule.is_active() and rule.matches_condition(context):
                applicable_rules.append(rule)

        return applicable_rules

    def evaluate_signature_requirements(
        self,
        context: ModelRuleCondition,
    ) -> ModelSignatureRequirements:
        """Evaluate signature requirements for given context."""
        applicable_rules = self.get_applicable_rules(context)

        # Start with global defaults
        requirements = ModelSignatureRequirements(
            minimum_signatures=self.global_minimum_signatures,
            required_algorithms=[],
            trusted_nodes=self.globally_trusted_nodes.copy(),
            compliance_tags=[],
            trust_level=self.default_trust_level,
            encryption_required=self.encryption_requirement.level != "none",
            certificate_validation=self.certificate_validation,
            applicable_rules=[rule.rule_id for rule in applicable_rules],
        )

        # Apply rules in order (later rules override earlier ones)
        for rule in applicable_rules:
            requirements.minimum_signatures = max(
                requirements.minimum_signatures, rule.minimum_signatures
            )

            if rule.required_algorithms:
                requirements.required_algorithms.extend(rule.required_algorithms)

            if rule.trusted_nodes:
                requirements.trusted_nodes.update(rule.trusted_nodes)

            if rule.compliance_tags:
                requirements.compliance_tags.extend(rule.compliance_tags)

        # Remove duplicates
        requirements.required_algorithms = list(set(requirements.required_algorithms))
        requirements.compliance_tags = list(set(requirements.compliance_tags))

        return requirements

    def validate_signature_chain(
        self,
        chain,
        context: ModelRuleCondition | None = None,
    ) -> ModelPolicyValidationResult:
        """Validate signature chain against policy."""
        if context is None:
            context = ModelRuleCondition()

        requirements = self.evaluate_signature_requirements(context)
        violations = []
        warnings = []

        # Check minimum signatures
        if len(chain.signatures) < requirements.minimum_signatures:
            violations.append(
                f"Insufficient signatures: {len(chain.signatures)} < {requirements.minimum_signatures}",
            )

        # Check signature algorithms
        if requirements.required_algorithms:
            chain_algorithms = {sig.algorithm for sig in chain.signatures}
            required_set = set(requirements.required_algorithms)
            if not required_set.intersection(chain_algorithms):
                violations.append(
                    f"Required algorithms not found: {required_set} not in {chain_algorithms}",
                )

        # Check trusted nodes
        if requirements.trusted_nodes:
            chain_signers = chain.get_unique_signers()
            trusted_in_chain = chain_signers.intersection(requirements.trusted_nodes)
            if not trusted_in_chain:
                violations.append("No signatures from trusted nodes")

        # Check blocked nodes
        chain_signers = chain.get_unique_signers()
        blocked_in_chain = chain_signers.intersection(self.blocked_nodes)
        if blocked_in_chain:
            violations.append(f"Signatures from blocked nodes: {blocked_in_chain}")

        # Check signature age
        max_age = timedelta(hours=self.maximum_signature_age_hours)
        current_time = datetime.utcnow()

        for signature in chain.signatures:
            age = current_time - signature.signed_at
            if age > max_age:
                warnings.append(
                    f"Signature {signature.signature_id} is too old: {age} > {max_age}",
                )

        # Check compliance requirements
        if requirements.compliance_tags:
            chain_compliance = set()
            for sig in chain.signatures:
                chain_compliance.update(sig.compliance_tags)

            missing_compliance = set(requirements.compliance_tags) - chain_compliance
            if missing_compliance:
                violations.append(f"Missing compliance tags: {missing_compliance}")

        # Determine overall status
        if violations:
            status = "violated"
            severity = ModelPolicySeverity()
        elif warnings:
            status = "warning"
            severity = ModelPolicySeverity()
        else:
            status = "compliant"
            severity = ModelPolicySeverity()

        return ModelPolicyValidationResult(
            policy_id=self.policy_id,
            policy_version=self.version,
            status=status,
            severity=severity,
            violations=violations,
            warnings=warnings,
            requirements=requirements,
            enforcement_mode=self.enforcement_mode,
            validated_at=current_time.isoformat(),
        )

    def create_default_rules(self) -> None:
        """Create default policy rules for common scenarios."""
        # High security rule for sensitive operations
        high_security_rule = PolicyRule(
            name="High Security Operations",
            description="Require multiple signatures for sensitive operations",
            conditions=ModelRuleCondition(
                operation_type_condition=ModelRuleConditionValue(
                    in_values=["financial", "healthcare", "pii"],
                ),
                security_level_condition=ModelRuleConditionValue(
                    gte=3,  # Assuming "high" maps to level 3
                ),
            ),
            minimum_signatures=3,
            required_algorithms=["RS256", "ES256"],
            compliance_tags=["SOX", "HIPAA", "GDPR"],
            violation_severity=ModelPolicySeverity(level="critical"),
        )

        # Production environment rule
        production_rule = PolicyRule(
            name="Production Environment",
            description="Enhanced security for production deployments",
            conditions=ModelRuleCondition(environment="production"),
            minimum_signatures=2,
            required_algorithms=["RS256", "ES256", "PS256"],
            audit_level="detailed",
            violation_severity=ModelPolicySeverity(),
        )

        # Development environment rule (more permissive)
        development_rule = PolicyRule(
            name="Development Environment",
            description="Relaxed requirements for development",
            conditions=ModelRuleCondition(environment="development"),
            minimum_signatures=1,
            allow_override=True,
            violation_severity=ModelPolicySeverity(level="warning"),
        )

        self.rules.extend([high_security_rule, production_rule, development_rule])

    def __str__(self) -> str:
        """Human-readable representation."""
        active_status = "active" if self.is_active() else "inactive"
        return f"TrustPolicy[{self.name}] v{self.version} ({active_status}, {len(self.rules)} rules)"
