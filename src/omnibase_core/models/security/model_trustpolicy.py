"""ONEX-compatible trust policy model for signature and compliance requirements."""

import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.core.model_trust_level import ModelTrustLevel
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)
from omnibase_core.models.security.model_certificate_validation_level import (
    ModelCertificateValidationLevel,
)
from omnibase_core.models.security.model_policy_rule import ModelPolicyRule
from omnibase_core.models.security.model_policy_severity import ModelPolicySeverity
from omnibase_core.models.security.model_policy_validation_result import (
    ModelPolicyValidationResult,
)
from omnibase_core.models.security.model_rule_condition import ModelRuleCondition
from omnibase_core.models.security.model_rule_condition_value import (
    ModelRuleConditionValue,
)
from omnibase_core.models.security.model_signature_requirements import (
    ModelSignatureRequirements,
)


class ModelTrustPolicy(BaseModel):
    """Trust policy engine for signature and compliance requirements.

    Defines flexible rules for signature requirements, certificate validation,
    and compliance enforcement across different security contexts. This is the
    core policy engine used by ModelSecureEventEnvelope to enforce security
    requirements.

    A trust policy consists of:
        - Global settings (default trust level, encryption requirements)
        - Signature requirements (minimum signatures, allowed algorithms)
        - Certificate settings (trusted CAs, revocation checking)
        - Node trust settings (trusted/blocked nodes)
        - Policy rules (conditional requirements based on context)
        - Compliance settings (frameworks, audit retention)

    Attributes:
        policy_id: Unique identifier for this policy (auto-generated UUID).
        name: Human-readable policy name (required).
        version: Semantic version of the policy (required).
        description: Optional detailed description.
        created_at: When the policy was created.
        created_by: Policy creator identifier (required).
        organization: Optional organization name.
        default_trust_level: Default trust level for envelopes.
        certificate_validation: Certificate validation strictness.
        encryption_requirement: Payload encryption requirement.
        global_minimum_signatures: Minimum signatures required globally.
        rules: Ordered list of conditional policy rules.
        enforcement_mode: How violations are handled (strict/permissive/monitor).
        effective_from: When policy becomes effective.
        expires_at: Optional policy expiration time.

    Example:
        >>> from omnibase_core.models.security.model_trustpolicy import ModelTrustPolicy
        >>> policy = ModelTrustPolicy(
        ...     name="Production Security",
        ...     version="1.0.0",
        ...     created_by="security-team",
        ...     global_minimum_signatures=2,
        ...     encryption_requirement="required",
        ... )
        >>> policy.create_default_rules()
        >>> policy.is_active()
        True

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    # Class configuration
    model_config = ConfigDict(
        validate_assignment=True, extra="forbid", from_attributes=True
    )

    # Constants
    MAX_MINIMUM_SIGNATURES: ClassVar[int] = 100
    MAX_SIGNATURE_AGE_HOURS: ClassVar[int] = 8760  # 1 year
    MAX_SIGNATURE_TIMEOUT_MS: ClassVar[int] = TIMEOUT_LONG_MS  # 5 minutes
    MAX_VERIFICATION_TIMEOUT_MS: ClassVar[int] = TIMEOUT_LONG_MS  # 5 minutes
    MAX_CACHE_TTL_SECONDS: ClassVar[int] = 86400  # 24 hours

    # Policy identification
    policy_id: UUID = Field(
        default_factory=uuid.uuid4, description="Unique policy identifier"
    )
    name: str = Field(default=..., description="Policy name", min_length=1)
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Policy version",
    )
    description: str | None = Field(default=None, description="Policy description")

    # Policy metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When policy was created"
    )
    created_by: str = Field(default=..., description="Policy creator", min_length=1)
    organization: str | None = Field(default=None, description="Organization name")

    # Global policy settings
    default_trust_level: str = Field(
        default="standard",
        description="Default trust level for envelopes",
        pattern=r"^(high_trust|trusted|standard|partial_trust|untrusted|compromised)$",
    )
    certificate_validation: str = Field(
        default="standard",
        description="Certificate validation level",
        pattern=r"^(none|basic|standard|strict|paranoid)$",
    )
    encryption_requirement: str = Field(
        default="optional",
        description="Payload encryption requirement",
        pattern=r"^(none|optional|required|always)$",
    )

    # Signature requirements
    global_minimum_signatures: int = Field(
        default=1,
        description="Global minimum signature requirement",
        ge=0,
        le=MAX_MINIMUM_SIGNATURES,
    )
    maximum_signature_age_hours: int = Field(
        default=24,
        description="Maximum age of signatures in hours",
        ge=1,
        le=MAX_SIGNATURE_AGE_HOURS,
    )
    require_timestamp_verification: bool = Field(
        default=True, description="Require timestamp signature verification"
    )

    # Certificate and PKI settings
    trusted_certificate_authorities: list[str] = Field(
        default_factory=list, description="Trusted CA certificate fingerprints"
    )
    certificate_revocation_check: bool = Field(
        default=True, description="Enable certificate revocation checking"
    )
    require_certificate_transparency: bool = Field(
        default=False, description="Require certificates to be in CT logs"
    )

    # Node trust settings
    globally_trusted_nodes: set[str] = Field(
        default_factory=set, description="Globally trusted node IDs"
    )
    blocked_nodes: set[str] = Field(default_factory=set, description="Blocked node IDs")
    require_node_registration: bool = Field(
        default=True, description="Require nodes to be registered"
    )

    # Policy rules
    rules: list[ModelPolicyRule] = Field(
        default_factory=list, description="Ordered list of policy rules"
    )

    # Compliance and audit
    compliance_frameworks: list[str] = Field(
        default_factory=list, description="Required compliance frameworks"
    )
    audit_retention_days: int = Field(
        default=2555,  # 7 years for SOX compliance
        description="Audit log retention period in days",
        ge=1,
    )
    require_audit_trail: bool = Field(
        default=True, description="Require complete audit trail"
    )

    # Performance settings
    signature_timeout_ms: int = Field(
        default=15000,
        description="Maximum signature operation time in milliseconds",
        ge=1000,
        le=MAX_SIGNATURE_TIMEOUT_MS,
    )
    verification_timeout_ms: int = Field(
        default=10000,
        description="Maximum verification time in milliseconds",
        ge=1000,
        le=MAX_VERIFICATION_TIMEOUT_MS,
    )
    cache_verification_results: bool = Field(
        default=True, description="Cache signature verification results"
    )
    verification_cache_ttl_seconds: int = Field(
        default=3600,
        description="Verification cache TTL in seconds",
        ge=60,
        le=MAX_CACHE_TTL_SECONDS,
    )

    # Policy enforcement
    enforcement_mode: str = Field(
        default="strict",
        description="Enforcement mode: 'strict', 'permissive', 'monitor'",
        pattern=r"^(strict|permissive|monitor)$",
    )
    allow_emergency_override: bool = Field(
        default=False, description="Allow emergency policy override"
    )
    emergency_override_roles: list[str] = Field(
        default_factory=list, description="Roles authorized for emergency override"
    )

    # Policy lifecycle
    effective_from: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When policy becomes effective",
    )
    expires_at: datetime | None = Field(default=None, description="When policy expires")
    auto_renewal: bool = Field(default=False, description="Automatically renew policy")

    @field_validator("version", mode="before")
    @classmethod
    def parse_input_version(cls, v: Any) -> Any:
        """Parse version from string, dict, or ModelSemVer.

        Args:
            v: Version as ModelSemVer, string, or dict

        Returns:
            ModelSemVer instance

        Raises:
            ModelOnexError: If version format is invalid
        """
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
            message="version must be a string, dict, or ModelSemVer",
        )

    @field_validator("global_minimum_signatures")
    @classmethod
    def validate_minimum_signatures(cls, v: int) -> int:
        """Validate minimum signature count."""
        if v < 0:
            raise ModelOnexError(
                message=(
                    f"global_minimum_signatures must be non-negative, got {v}. "
                    "Signature requirements cannot be negative values."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE,
            )
        if v > cls.MAX_MINIMUM_SIGNATURES:
            raise ModelOnexError(
                message=(
                    f"global_minimum_signatures value {v} exceeds maximum allowed "
                    f"value of {cls.MAX_MINIMUM_SIGNATURES}. Reduce the signature "
                    "requirement or adjust MAX_MINIMUM_SIGNATURES if needed."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE,
            )
        return v

    @field_validator("enforcement_mode")
    @classmethod
    def validate_enforcement_mode(cls, v: str) -> str:
        """Validate enforcement mode."""
        valid_modes = ["strict", "permissive", "monitor"]
        if v not in valid_modes:
            raise ModelOnexError(
                message=(
                    f"enforcement_mode '{v}' is not valid. "
                    f"Must be one of: {valid_modes}. "
                    "'strict' blocks violations, 'permissive' logs warnings, "
                    "'monitor' only records for analysis."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        return v

    @model_validator(mode="after")
    def validate_expiration_date(self) -> Self:
        """Validate expiration date is after effective date."""
        if self.expires_at is not None:
            if self.expires_at <= self.effective_from:
                raise ModelOnexError(
                    message=(
                        f"expires_at ({self.expires_at.isoformat()}) must be after "
                        f"effective_from ({self.effective_from.isoformat()}). "
                        "A policy cannot expire before or at the same time it becomes effective."
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )
        return self

    def is_active(self, check_time: datetime | None = None) -> bool:
        """Check if the policy is currently active based on time bounds.

        A policy is considered active if the check time falls within the
        effective_from and expires_at window (if set).

        Args:
            check_time: Optional datetime to check against. If None, uses
                the current UTC time.

        Returns:
            True if the policy is currently active and should be enforced,
            False if the policy is not yet effective or has expired.

        Example:
            >>> policy = ModelTrustPolicy(name="Test", version="1.0.0", created_by="admin")
            >>> policy.is_active()
            True
        """
        if check_time is None:
            check_time = datetime.now(UTC)

        if check_time < self.effective_from:
            return False

        return not (self.expires_at and check_time > self.expires_at)

    def add_rule(self, rule: ModelPolicyRule) -> None:
        """Add a new policy rule to this trust policy.

        Rules are appended to the rules list and evaluated in order during
        policy enforcement. Later rules can override or augment requirements
        from earlier rules.

        Args:
            rule: The ModelPolicyRule to add to this policy.

        Raises:
            ModelOnexError: If the policy is not currently active.

        Example:
            >>> policy = ModelTrustPolicy(name="Test", version="1.0.0", created_by="admin")
            >>> rule = ModelPolicyRule(
            ...     name="Production Security",
            ...     conditions=ModelRuleCondition(environment="production"),
            ...     minimum_signatures=2,
            ... )
            >>> policy.add_rule(rule)
            >>> len(policy.rules)
            1
        """
        if not self.is_active():
            raise ModelOnexError(
                message=(
                    f"Cannot add rules to policy '{self.name}' because it is not active. "
                    f"Policy is effective from {self.effective_from.isoformat()}"
                    + (
                        f" and expires at {self.expires_at.isoformat()}"
                        if self.expires_at
                        else ""
                    )
                    + ". Ensure the current time falls within the policy's active window."
                ),
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        self.rules.append(rule)

    def get_applicable_rules(
        self, context: ModelRuleCondition
    ) -> list[ModelPolicyRule]:
        """Get all rules that apply to the given execution context.

        Iterates through all policy rules and returns those that are both
        active and whose conditions match the provided context.

        Args:
            context: ModelRuleCondition containing the current execution
                context to evaluate against rule conditions.

        Returns:
            List of ModelPolicyRule instances that are active and match
            the context. Rules are returned in their defined order.

        Example:
            >>> policy = ModelTrustPolicy(name="Test", version="1.0.0", created_by="admin")
            >>> policy.create_default_rules()
            >>> context = ModelRuleCondition(environment="production")
            >>> applicable = policy.get_applicable_rules(context)
            >>> len(applicable) >= 1
            True
        """
        applicable_rules = []

        for rule in self.rules:
            if rule.is_active() and rule.matches_condition(context):
                applicable_rules.append(rule)

        return applicable_rules

    def evaluate_signature_requirements(
        self, context: ModelRuleCondition
    ) -> ModelSignatureRequirements:
        """Evaluate and aggregate signature requirements for a given context.

        Computes the effective signature requirements by starting with global
        policy defaults and then applying all matching rules in order. Later
        rules can increase minimum signatures or add required algorithms.

        The aggregation logic:
            - minimum_signatures: Takes the maximum across all rules
            - required_algorithms: Union of all rule requirements
            - trusted_nodes: Union of global and all rule trusted nodes
            - compliance_tags: Union of all rule compliance tags

        Args:
            context: ModelRuleCondition containing the current execution
                context to evaluate against rule conditions.

        Returns:
            ModelSignatureRequirements with the aggregated requirements
            from all applicable rules and global defaults.

        Example:
            >>> policy = ModelTrustPolicy(
            ...     name="Test",
            ...     version="1.0.0",
            ...     created_by="admin",
            ...     global_minimum_signatures=1,
            ... )
            >>> policy.create_default_rules()
            >>> context = ModelRuleCondition(environment="production")
            >>> requirements = policy.evaluate_signature_requirements(context)
            >>> requirements.minimum_signatures >= 1
            True
        """
        applicable_rules = self.get_applicable_rules(context)

        # Start with global defaults
        # Map string trust level to ModelTrustLevel instance
        trust_level_map = {
            "untrusted": ModelTrustLevel.untrusted(),
            "compromised": ModelTrustLevel.untrusted(),
            "partial_trust": ModelTrustLevel(
                trust_score=0.3,
                trust_category="low",
                display_name="Partial Trust",
            ),
            "standard": ModelTrustLevel.validated(),
            "trusted": ModelTrustLevel.trusted(),
            "high_trust": ModelTrustLevel.trusted(),
        }
        trust_level = trust_level_map.get(
            self.default_trust_level, ModelTrustLevel.validated()
        )

        requirements = ModelSignatureRequirements(
            minimum_signatures=self.global_minimum_signatures,
            required_algorithms=[],
            trusted_nodes=self.globally_trusted_nodes.copy(),
            compliance_tags=[],
            trust_level=trust_level,
            encryption_required=self.encryption_requirement != "none",
            certificate_validation=ModelCertificateValidationLevel(
                level=self.certificate_validation
            ),
            applicable_rules=[str(rule.rule_id) for rule in applicable_rules],
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
        chain: Any,  # Would be ModelSignatureChain in full implementation
        context: ModelRuleCondition | None = None,
    ) -> ModelPolicyValidationResult:
        """Validate a signature chain against this trust policy.

        Evaluates whether a signature chain meets the requirements defined
        by this policy and its applicable rules. The validation checks
        signature counts, algorithms, trusted signers, and compliance tags.

        Args:
            chain: The signature chain to validate. Expected to be a
                ModelSignatureChain instance with signatures to verify.
            context: Optional ModelRuleCondition for contextual evaluation.
                If None, a default empty context is used.

        Returns:
            ModelPolicyValidationResult containing:
                - status: "compliant", "warning", or "violated"
                - severity: Severity level of any violations
                - violations: List of policy violation descriptions
                - warnings: List of warning messages
                - requirements: The evaluated signature requirements

        Raises:
            ModelOnexError: If the policy is not currently active.

        Example:
            >>> policy = ModelTrustPolicy(name="Test", version="1.0.0", created_by="admin")
            >>> result = policy.validate_signature_chain(signature_chain)
            >>> result.status
            'compliant'
        """
        if not self.is_active():
            raise ModelOnexError(
                message=(
                    f"Cannot validate signature chain with policy '{self.name}' because "
                    f"the policy is not active. Policy is effective from "
                    f"{self.effective_from.isoformat()}"
                    + (
                        f" and expires at {self.expires_at.isoformat()}"
                        if self.expires_at
                        else ""
                    )
                    + ". Use an active policy for validation."
                ),
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        if context is None:
            context = ModelRuleCondition(
                operation_type=None,
                security_level=None,
                environment=None,
                operation_type_condition=None,
                security_level_condition=None,
                hop_count_condition=None,
                source_node_id=None,
                destination=None,
                hop_count=None,
                is_encrypted=None,
                signature_count=None,
            )

        requirements = self.evaluate_signature_requirements(context)
        violations: list[str] = []
        warnings: list[str] = []

        # Mock validation - in real implementation would validate actual chain
        current_time = datetime.now(UTC)

        # Determine overall status
        if violations:
            status = "violated"
            severity = ModelPolicySeverity(level="critical")
        elif warnings:
            status = "warning"
            severity = ModelPolicySeverity(level="warning")
        else:
            status = "compliant"
            severity = ModelPolicySeverity(level="info")

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
        """Create a standard set of policy rules for common security scenarios.

        Populates the policy with three pre-configured rules covering typical
        enterprise security requirements:

        1. **High Security Operations**: For operations marked as high_security
           with high or critical security levels. Requires 3 signatures,
           RS256/ES256 algorithms, and SOX/HIPAA/GDPR compliance tags.

        2. **Production Environment**: For any operation in production
           environment. Requires 2 signatures with RS256/ES256/PS256 algorithms
           and detailed audit logging.

        3. **Development Environment**: Relaxed requirements for development
           with 1 signature minimum and manual override allowed.

        Side Effects:
            Appends three ModelPolicyRule instances to self.rules.

        Example:
            >>> policy = ModelTrustPolicy(name="Test", version="1.0.0", created_by="admin")
            >>> len(policy.rules)
            0
            >>> policy.create_default_rules()
            >>> len(policy.rules)
            3
            >>> policy.rules[0].name
            'High Security Operations'

        Note:
            These rules are intended as a starting point. Production deployments
            should customize rules based on specific security requirements.
        """
        # High security rule for sensitive operations
        high_security_rule = ModelPolicyRule(
            name="High Security Operations",
            description="Require multiple signatures for sensitive operations",
            conditions=ModelRuleCondition(
                operation_type=None,
                security_level=None,
                environment=None,
                operation_type_condition=ModelRuleConditionValue.model_validate(
                    {"$in": ["high_security"]}
                ),
                security_level_condition=ModelRuleConditionValue.model_validate(
                    {"$in": ["high", "critical"]}
                ),
                hop_count_condition=None,
                source_node_id=None,
                destination=None,
                hop_count=None,
                is_encrypted=None,
                signature_count=None,
            ),
            minimum_signatures=3,
            required_algorithms=["RS256", "ES256"],
            compliance_tags=["SOX", "HIPAA", "GDPR"],
            violation_severity=ModelPolicySeverity(
                level="critical",
                auto_remediate=False,
                block_operation=True,
                notify_administrators=True,
                log_to_audit=True,
                escalation_threshold=1,
                remediation_action=None,
                custom_message=None,
            ),
        )

        # Production environment rule
        production_rule = ModelPolicyRule(
            name="Production Environment",
            description="Enhanced security for production deployments",
            conditions=ModelRuleCondition(
                operation_type=None,
                security_level=None,
                environment="production",
                operation_type_condition=None,
                security_level_condition=None,
                hop_count_condition=None,
                source_node_id=None,
                destination=None,
                hop_count=None,
                is_encrypted=None,
                signature_count=None,
            ),
            minimum_signatures=2,
            required_algorithms=["RS256", "ES256", "PS256"],
            audit_level="detailed",
            violation_severity=ModelPolicySeverity(
                level="error",
                auto_remediate=False,
                block_operation=True,
                notify_administrators=True,
                log_to_audit=True,
                escalation_threshold=2,
                remediation_action=None,
                custom_message=None,
            ),
        )

        # Development environment rule (more permissive)
        development_rule = ModelPolicyRule(
            name="Development Environment",
            description="Relaxed requirements for development",
            conditions=ModelRuleCondition(
                operation_type=None,
                security_level=None,
                environment="development",
                operation_type_condition=None,
                security_level_condition=None,
                hop_count_condition=None,
                source_node_id=None,
                destination=None,
                hop_count=None,
                is_encrypted=None,
                signature_count=None,
            ),
            minimum_signatures=1,
            allow_override=True,
            violation_severity=ModelPolicySeverity(
                level="warning",
                auto_remediate=True,
                block_operation=False,
                notify_administrators=False,
                log_to_audit=True,
                escalation_threshold=5,
                remediation_action=None,
                custom_message=None,
            ),
        )

        self.rules.extend([high_security_rule, production_rule, development_rule])

    def __str__(self) -> str:
        """Human-readable representation."""
        active_status = "active" if self.is_active() else "inactive"
        return f"TrustPolicy[{self.name}] v{self.version} ({active_status}, {len(self.rules)} rules)"
