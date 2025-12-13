"""
ModelPermissionConstraints - Permission constraints configuration

Permission constraints model for defining additional limitations and requirements
including usage limits, approval requirements, delegation rules, and audit requirements.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .model_approval_requirements import ModelApprovalRequirements
from .model_audit_requirements import ModelAuditRequirements
from .model_permission_constraint_metadata import ModelPermissionConstraintMetadata
from .model_permission_custom_constraints import ModelPermissionCustomConstraints
from .model_permission_session_info import ModelPermissionSessionInfo
from .model_risk_assessment import ModelRiskAssessment


class ModelPermissionConstraints(BaseModel):
    """
    Permission constraints configuration model

    This model defines additional constraints and limitations for permissions
    including usage limits, approval workflows, delegation rules, and audit requirements.
    """

    constraints_id: UUID = Field(
        default=...,
        description="Unique constraints identifier",
    )

    usage_limits_enabled: bool = Field(
        default=False,
        description="Whether usage limits are enabled",
    )

    max_uses_total: int | None = Field(
        default=None,
        description="Maximum total uses of this permission",
        ge=0,
    )

    max_uses_per_day: int | None = Field(
        default=None,
        description="Maximum uses per day",
        ge=0,
    )

    max_uses_per_hour: int | None = Field(
        default=None,
        description="Maximum uses per hour",
        ge=0,
    )

    max_concurrent_uses: int | None = Field(
        default=None,
        description="Maximum concurrent uses",
        ge=1,
    )

    cooldown_period_minutes: int | None = Field(
        default=None,
        description="Cooldown period between uses in minutes",
        ge=0,
    )

    usage_window_minutes: int | None = Field(
        default=None,
        description="Time window for usage tracking in minutes",
        ge=1,
    )

    approval_required: bool = Field(
        default=False,
        description="Whether approval is required before use",
    )

    approval_types: list[str] = Field(
        default_factory=list,
        description="Types of approval required (e.g., 'manager', 'security', 'admin')",
    )

    min_approvals_required: int = Field(
        default=1,
        description="Minimum number of approvals required",
        ge=0,
    )

    approval_timeout_hours: int | None = Field(
        default=None,
        description="Hours after which approval request expires",
        ge=1,
    )

    auto_approve_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions under which approval is automatic",
    )

    delegation_allowed: bool = Field(
        default=False,
        description="Whether this permission can be delegated",
    )

    max_delegation_depth: int = Field(
        default=1,
        description="Maximum depth of delegation chain",
        ge=0,
        le=10,
    )

    delegation_requires_approval: bool = Field(
        default=True,
        description="Whether delegation requires approval",
    )

    delegate_inheritance_rules: list[str] = Field(
        default_factory=list,
        description="Rules for what delegates inherit (e.g., 'subset_only', 'time_limited')",
    )

    audit_logging_enabled: bool = Field(
        default=True,
        description="Whether audit logging is enabled for this permission",
    )

    audit_detail_level: str = Field(
        default="standard",
        description="Level of audit detail required",
        pattern="^(minimal|standard|detailed|comprehensive)$",
    )

    audit_retention_days: int = Field(
        default=365,
        description="Days to retain audit logs",
        ge=1,
    )

    audit_export_required: bool = Field(
        default=False,
        description="Whether audit logs must be exported to external system",
    )

    notification_enabled: bool = Field(
        default=False,
        description="Whether notifications are enabled for permission use",
    )

    notification_recipients: list[str] = Field(
        default_factory=list,
        description="Recipients for permission use notifications",
    )

    notification_threshold: int | None = Field(
        default=None,
        description="Usage threshold that triggers notifications",
        ge=1,
    )

    risk_level: str = Field(
        default="medium",
        description="Risk level of this permission",
        pattern="^(low|medium|high|critical)$",
    )

    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Compliance frameworks this permission relates to",
    )

    data_classification_required: str | None = Field(
        default=None,
        description="Required data classification level for resources",
        pattern="^(public|internal|confidential|restricted|top_secret)$",
    )

    emergency_override_allowed: bool = Field(
        default=False,
        description="Whether emergency override is allowed",
    )

    emergency_override_approvers: list[str] = Field(
        default_factory=list,
        description="Who can approve emergency overrides",
    )

    break_glass_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions under which break glass access is allowed",
    )

    session_constraints_enabled: bool = Field(
        default=False,
        description="Whether session-specific constraints are enabled",
    )

    max_session_duration_minutes: int | None = Field(
        default=None,
        description="Maximum session duration in minutes",
        ge=1,
    )

    session_idle_timeout_minutes: int | None = Field(
        default=None,
        description="Session idle timeout in minutes",
        ge=1,
    )

    require_mfa: bool = Field(
        default=False,
        description="Whether multi-factor authentication is required",
    )

    mfa_validity_minutes: int | None = Field(
        default=None,
        description="How long MFA verification is valid in minutes",
        ge=1,
    )

    network_constraints_enabled: bool = Field(
        default=False,
        description="Whether network constraints are enabled",
    )

    allowed_networks: list[str] = Field(
        default_factory=list,
        description="CIDR blocks of allowed networks",
    )

    blocked_networks: list[str] = Field(
        default_factory=list,
        description="CIDR blocks of blocked networks",
    )

    require_secure_connection: bool = Field(
        default=False,
        description="Whether secure connection (TLS) is required",
    )

    custom_constraints: ModelPermissionCustomConstraints | None = Field(
        default=None,
        description="Custom constraint definitions",
    )

    constraint_metadata: ModelPermissionConstraintMetadata | None = Field(
        default=None,
        description="Additional constraint metadata",
    )

    def is_usage_allowed(self, current_usage: dict[str, int]) -> bool:
        """Check if usage is allowed based on current usage statistics"""
        if not self.usage_limits_enabled:
            return True

        # Check total usage
        if self.max_uses_total and current_usage.get("total", 0) >= self.max_uses_total:
            return False

        # Check daily usage
        if (
            self.max_uses_per_day
            and current_usage.get("today", 0) >= self.max_uses_per_day
        ):
            return False

        # Check hourly usage
        if (
            self.max_uses_per_hour
            and current_usage.get("this_hour", 0) >= self.max_uses_per_hour
        ):
            return False

        # Check concurrent usage
        return not (
            self.max_concurrent_uses
            and current_usage.get("concurrent", 0) >= self.max_concurrent_uses
        )

    def calculate_cooldown_end(self, last_use: datetime) -> datetime | None:
        """Calculate when cooldown period ends"""
        if not self.cooldown_period_minutes:
            return None

        return last_use + timedelta(minutes=self.cooldown_period_minutes)

    def is_cooldown_satisfied(self, last_use: datetime | None) -> bool:
        """Check if cooldown period is satisfied"""
        if not self.cooldown_period_minutes or not last_use:
            return True

        cooldown_end = self.calculate_cooldown_end(last_use)
        return cooldown_end is not None and datetime.now(UTC) >= cooldown_end

    def get_approval_requirements(self) -> ModelApprovalRequirements:
        """Get approval requirements for this permission"""
        return ModelApprovalRequirements(
            required=self.approval_required,
            types=self.approval_types,
            min_approvals=self.min_approvals_required,
            timeout_hours=self.approval_timeout_hours,
            auto_approve_conditions=self.auto_approve_conditions,
            escalation_enabled=False,
            escalation_chain=[],
            approval_message_template=None,
        )

    def can_delegate_to(self, target_user: str, delegation_depth: int = 0) -> bool:
        """Check if permission can be delegated to target user"""
        if not self.delegation_allowed:
            return False

        if delegation_depth >= self.max_delegation_depth:
            return False

        # Additional delegation rules would be evaluated here
        return True

    def get_audit_requirements(self) -> ModelAuditRequirements:
        """Get audit requirements for this permission"""
        return ModelAuditRequirements(
            enabled=self.audit_logging_enabled,
            detail_level=self.audit_detail_level,
            retention_days=self.audit_retention_days,
            export_required=self.audit_export_required,
            compliance_tags=self.compliance_tags,
            export_destinations=[],
            export_format="json",
            redaction_rules=[],
            sampling_rate=1.0,
            alert_on_anomaly=False,
            archive_after_days=None,
        )

    def should_notify(self, usage_count: int) -> bool:
        """Check if notification should be sent based on usage"""
        if not self.notification_enabled:
            return False

        return bool(
            self.notification_threshold and usage_count >= self.notification_threshold,
        )

    def get_risk_assessment(self) -> ModelRiskAssessment:
        """Get risk assessment information"""
        risk_scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        return ModelRiskAssessment(
            level=self.risk_level,
            score=risk_scores.get(self.risk_level, 2),
            compliance_tags=self.compliance_tags,
            data_classification_required=self.data_classification_required,
            emergency_override_allowed=self.emergency_override_allowed,
            threat_categories=[],
            mitigation_controls=[],
            residual_risk_acceptable=True,
            risk_owner=None,
            review_frequency_days=90,
            last_review_date=None,
            next_review_date=None,
        )

    def validate_session_constraints(
        self,
        session_info: ModelPermissionSessionInfo,
    ) -> bool:
        """Validate session-specific constraints"""
        if not self.session_constraints_enabled:
            return True

        # Check session duration
        if self.max_session_duration_minutes:
            session_duration = (
                datetime.now(UTC) - session_info.start_time
            ).total_seconds() / 60
            if session_duration > self.max_session_duration_minutes:
                return False

        # Check idle timeout
        if self.session_idle_timeout_minutes:
            idle_time = (
                datetime.now(UTC) - session_info.last_activity
            ).total_seconds() / 60
            if idle_time > self.session_idle_timeout_minutes:
                return False

        return True

    def is_network_allowed(self, ip_address: str) -> bool:
        """Check if access from IP address is allowed"""
        if not self.network_constraints_enabled:
            return True

        # Check blocked networks first
        if self.blocked_networks:
            for blocked_cidr in self.blocked_networks:
                if self._ip_in_cidr(ip_address, blocked_cidr):
                    return False

        # Check allowed networks
        if self.allowed_networks:
            for allowed_cidr in self.allowed_networks:
                if self._ip_in_cidr(ip_address, allowed_cidr):
                    return True
            return False  # Not in any allowed network

        return True

    def _ip_in_cidr(self, ip_address: str, cidr: str) -> bool:
        """Check if IP address is in CIDR block (simplified implementation)"""
        # This is a simplified implementation
        # In production, would use proper IP address libraries

        if "/" not in cidr:
            return ip_address == cidr

        network, _ = cidr.split("/")
        # Simplified check - in production use ipaddress module
        return ip_address.startswith(network.rsplit(".", 1)[0])

    @classmethod
    def create_standard_constraints(
        cls,
        risk_level: str = "medium",
    ) -> "ModelPermissionConstraints":
        """Create standard permission constraints"""
        audit_detail = "standard" if risk_level in ["low", "medium"] else "detailed"
        requires_approval = risk_level in ["high", "critical"]

        return cls(
            constraints_id=uuid4(),
            risk_level=risk_level,
            audit_logging_enabled=True,
            audit_detail_level=audit_detail,
            approval_required=requires_approval,
            min_approvals_required=1 if requires_approval else 0,
            delegation_allowed=risk_level in ["low", "medium"],
            max_uses_total=None,
            max_uses_per_day=None,
            max_uses_per_hour=None,
            max_concurrent_uses=None,
            cooldown_period_minutes=None,
            usage_window_minutes=None,
            approval_timeout_hours=None,
            notification_threshold=None,
            data_classification_required=None,
            max_session_duration_minutes=None,
            session_idle_timeout_minutes=None,
            mfa_validity_minutes=None,
            custom_constraints=None,
            constraint_metadata=None,
        )

    @classmethod
    def create_high_security_constraints(cls) -> "ModelPermissionConstraints":
        """Create high security permission constraints"""
        return cls(
            constraints_id=uuid4(),
            usage_limits_enabled=True,
            max_uses_total=None,
            max_uses_per_day=10,
            max_uses_per_hour=3,
            max_concurrent_uses=None,
            cooldown_period_minutes=None,
            usage_window_minutes=None,
            approval_required=True,
            approval_types=["security", "manager"],
            min_approvals_required=2,
            approval_timeout_hours=None,
            notification_threshold=None,
            data_classification_required=None,
            delegation_allowed=False,
            audit_logging_enabled=True,
            audit_detail_level="comprehensive",
            notification_enabled=True,
            risk_level="critical",
            max_session_duration_minutes=None,
            session_idle_timeout_minutes=None,
            mfa_validity_minutes=None,
            require_mfa=True,
            network_constraints_enabled=True,
            require_secure_connection=True,
            custom_constraints=None,
            constraint_metadata=None,
        )

    @classmethod
    def create_emergency_constraints(cls) -> "ModelPermissionConstraints":
        """Create emergency access permission constraints"""
        return cls(
            constraints_id=uuid4(),
            usage_limits_enabled=True,
            max_uses_total=1,
            max_uses_per_day=None,
            max_uses_per_hour=None,
            max_concurrent_uses=None,
            cooldown_period_minutes=None,
            usage_window_minutes=None,
            approval_required=False,  # Emergency access doesn't wait for approval
            approval_timeout_hours=None,
            notification_threshold=None,
            data_classification_required=None,
            audit_logging_enabled=True,
            audit_detail_level="comprehensive",
            notification_enabled=True,
            notification_recipients=["security-team", "compliance"],
            risk_level="critical",
            emergency_override_allowed=True,
            break_glass_conditions=["system_outage", "security_incident"],
            session_constraints_enabled=True,
            max_session_duration_minutes=60,
            session_idle_timeout_minutes=None,
            mfa_validity_minutes=None,
            require_mfa=True,
            custom_constraints=None,
            constraint_metadata=None,
        )
