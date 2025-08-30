"""
Security assessment model to replace Dict[str, Any] usage for security data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.model.core.enum_security_risk_level import SecurityRiskLevel
from omnibase_core.model.core.model_security_vulnerability import \
    ModelSecurityVulnerability

# Backward compatibility alias
SecurityVulnerability = ModelSecurityVulnerability


class ModelSecurityAssessment(BaseModel):
    """
    Security assessment with typed fields.
    Replaces Dict[str, Any] for get_security_assessment() returns.
    """

    # Overall assessment
    overall_risk_level: SecurityRiskLevel = Field(
        ..., description="Overall security risk level"
    )
    security_score: Optional[float] = Field(None, description="Security score (0-100)")
    last_assessment_date: datetime = Field(
        default_factory=datetime.utcnow, description="Last assessment date"
    )

    # Vulnerabilities
    vulnerabilities: List[ModelSecurityVulnerability] = Field(
        default_factory=list, description="Identified vulnerabilities"
    )
    vulnerability_count: Dict[str, int] = Field(
        default_factory=dict, description="Count by severity level"
    )

    # Security controls
    authentication_enabled: Optional[bool] = Field(
        None, description="Whether authentication is enabled"
    )
    authorization_enabled: Optional[bool] = Field(
        None, description="Whether authorization is enabled"
    )
    encryption_at_rest: Optional[bool] = Field(
        None, description="Whether data is encrypted at rest"
    )
    encryption_in_transit: Optional[bool] = Field(
        None, description="Whether data is encrypted in transit"
    )

    # Access controls
    access_control_model: Optional[str] = Field(
        None, description="Access control model (RBAC/ABAC/etc)"
    )
    privileged_accounts: Optional[int] = Field(
        None, description="Number of privileged accounts"
    )
    service_accounts: Optional[int] = Field(
        None, description="Number of service accounts"
    )
    mfa_enabled: Optional[bool] = Field(None, description="Whether MFA is enabled")

    # Compliance
    compliance_standards: List[str] = Field(
        default_factory=list, description="Compliance standards met"
    )
    compliance_violations: List[str] = Field(
        default_factory=list, description="Compliance violations found"
    )
    last_compliance_audit: Optional[datetime] = Field(
        None, description="Last compliance audit date"
    )

    # Security monitoring
    security_monitoring_enabled: Optional[bool] = Field(
        None, description="Whether monitoring is enabled"
    )
    intrusion_detection_enabled: Optional[bool] = Field(
        None, description="Whether IDS is enabled"
    )
    anomaly_detection_enabled: Optional[bool] = Field(
        None, description="Whether anomaly detection is enabled"
    )
    security_alerts_last_24h: Optional[int] = Field(
        None, description="Security alerts in last 24 hours"
    )

    # Security practices
    security_training_compliance: Optional[float] = Field(
        None, description="Security training compliance rate"
    )
    last_penetration_test: Optional[datetime] = Field(
        None, description="Last penetration test date"
    )
    last_security_review: Optional[datetime] = Field(
        None, description="Last security review date"
    )
    security_patches_pending: Optional[int] = Field(
        None, description="Number of pending security patches"
    )

    # Recommendations
    critical_recommendations: List[str] = Field(
        default_factory=list, description="Critical security recommendations"
    )
    improvement_recommendations: List[str] = Field(
        default_factory=list, description="Security improvement recommendations"
    )

    # Metadata
    assessment_methodology: Optional[str] = Field(
        None, description="Assessment methodology used"
    )
    assessment_tools: List[str] = Field(
        default_factory=list, description="Tools used for assessment"
    )
    assessed_by: Optional[str] = Field(None, description="Who performed the assessment")
    next_assessment_date: Optional[datetime] = Field(
        None, description="Next scheduled assessment"
    )

    model_config = ConfigDict()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility."""
        return self.dict(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelSecurityAssessment":
        """Create from dictionary for easy migration."""
        return cls(**data)

    @field_serializer(
        "last_assessment_date",
        "last_compliance_audit",
        "last_penetration_test",
        "last_security_review",
        "next_assessment_date",
    )
    def serialize_datetime(self, value):
        if value and isinstance(value, datetime):
            return value.isoformat()
        return value
