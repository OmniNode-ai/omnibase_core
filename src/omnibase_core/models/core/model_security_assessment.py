"""
Security assessment model to replace Dict[str, Any] usage for security data.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_serializer

if TYPE_CHECKING:
    from omnibase_core.types.type_serializable_value import SerializedDict

from omnibase_core.enums.enum_security_risk_level import EnumSecurityRiskLevel
from omnibase_core.models.core.model_security_vulnerability import (
    ModelSecurityVulnerability,
)

# Compatibility alias
SecurityVulnerability = ModelSecurityVulnerability


class ModelSecurityAssessment(BaseModel):
    """
    Security assessment with typed fields.
    Replaces Dict[str, Any] for get_security_assessment() returns.
    """

    # Overall assessment
    overall_risk_level: EnumSecurityRiskLevel = Field(
        default=...,
        description="Overall security risk level",
    )
    security_score: float | None = Field(
        default=None, description="Security score (0-100)"
    )
    last_assessment_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last assessment date",
    )

    # Vulnerabilities
    vulnerabilities: list[ModelSecurityVulnerability] = Field(
        default_factory=list,
        description="Identified vulnerabilities",
    )
    vulnerability_count: dict[str, int] = Field(
        default_factory=dict,
        description="Count by severity level",
    )

    # Security controls
    authentication_enabled: bool | None = Field(
        default=None,
        description="Whether authentication is enabled",
    )
    authorization_enabled: bool | None = Field(
        default=None,
        description="Whether authorization is enabled",
    )
    encryption_at_rest: bool | None = Field(
        default=None,
        description="Whether data is encrypted at rest",
    )
    encryption_in_transit: bool | None = Field(
        default=None,
        description="Whether data is encrypted in transit",
    )

    # Access controls
    access_control_model: str | None = Field(
        default=None,
        description="Access control model (RBAC/ABAC/etc)",
    )
    privileged_accounts: int | None = Field(
        default=None,
        description="Number of privileged accounts",
    )
    service_accounts: int | None = Field(
        default=None,
        description="Number of service accounts",
    )
    mfa_enabled: bool | None = Field(default=None, description="Whether MFA is enabled")

    # Compliance
    compliance_standards: list[str] = Field(
        default_factory=list,
        description="Compliance standards met",
    )
    compliance_violations: list[str] = Field(
        default_factory=list,
        description="Compliance violations found",
    )
    last_compliance_audit: datetime | None = Field(
        default=None,
        description="Last compliance audit date",
    )

    # Security monitoring
    security_monitoring_enabled: bool | None = Field(
        default=None,
        description="Whether monitoring is enabled",
    )
    intrusion_detection_enabled: bool | None = Field(
        default=None,
        description="Whether IDS is enabled",
    )
    anomaly_detection_enabled: bool | None = Field(
        default=None,
        description="Whether anomaly detection is enabled",
    )
    security_alerts_last_24h: int | None = Field(
        default=None,
        description="Security alerts in last 24 hours",
    )

    # Security practices
    security_training_compliance: float | None = Field(
        default=None,
        description="Security training compliance rate",
    )
    last_penetration_test: datetime | None = Field(
        default=None,
        description="Last penetration test date",
    )
    last_security_review: datetime | None = Field(
        default=None,
        description="Last security review date",
    )
    security_patches_pending: int | None = Field(
        default=None,
        description="Number of pending security patches",
    )

    # Recommendations
    critical_recommendations: list[str] = Field(
        default_factory=list,
        description="Critical security recommendations",
    )
    improvement_recommendations: list[str] = Field(
        default_factory=list,
        description="Security improvement recommendations",
    )

    # Metadata
    assessment_methodology: str | None = Field(
        default=None,
        description="Assessment methodology used",
    )
    assessment_tools: list[str] = Field(
        default_factory=list,
        description="Tools used for assessment",
    )
    assessed_by: str | None = Field(
        default=None, description="Who performed the assessment"
    )
    next_assessment_date: datetime | None = Field(
        default=None,
        description="Next scheduled assessment",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    @classmethod
    def from_dict(cls, data: "SerializedDict") -> "ModelSecurityAssessment":
        """Create from dictionary for easy migration."""
        return cls.model_validate(data)

    @field_serializer(
        "last_assessment_date",
        "last_compliance_audit",
        "last_penetration_test",
        "last_security_review",
        "next_assessment_date",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value:
            return value.isoformat()
        return None
