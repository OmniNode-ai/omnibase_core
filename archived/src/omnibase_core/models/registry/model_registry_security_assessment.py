"""
Registry Security Assessment Model

Type-safe security assessment for registry validation.
"""

from pydantic import BaseModel, Field


class ModelRegistrySecurityAssessment(BaseModel):
    """
    Type-safe security assessment for registry validation.

    Provides structured security risk analysis and recommendations.
    """

    overall_security_risk: str = Field(
        "LOW",
        description="Overall security risk level",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    vulnerability_count: int = Field(
        0,
        description="Number of vulnerabilities detected",
        ge=0,
    )

    critical_vulnerabilities: int = Field(
        0,
        description="Number of critical vulnerabilities",
        ge=0,
    )

    security_tools_missing: bool = Field(
        False,
        description="Whether security tools are missing",
    )

    authentication_risk: str = Field(
        "LOW",
        description="Authentication risk level",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    authorization_risk: str = Field(
        "LOW",
        description="Authorization risk level",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    data_protection_risk: str = Field(
        "LOW",
        description="Data protection risk level",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    network_security_risk: str = Field(
        "LOW",
        description="Network security risk level",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    compliance_violations: list[str] = Field(
        default_factory=list,
        description="List of compliance violations",
    )

    security_recommendations: list[str] = Field(
        default_factory=list,
        description="Security improvement recommendations",
    )

    last_security_scan: str | None = Field(
        None,
        description="Timestamp of last security scan (ISO format)",
    )

    security_score: float = Field(
        1.0,
        description="Security score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    requires_immediate_action: bool = Field(
        False,
        description="Whether immediate security action is required",
    )
