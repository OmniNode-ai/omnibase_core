"""
ModelCredentialsAnalysis: Credentials strength analysis results.

This model provides structured credentials analysis without using Any types.
"""

from pydantic import BaseModel, Field


class ModelManagerAssessment(BaseModel):
    """Manager-specific assessment details."""

    backend_security_level: str = Field(..., description="Backend security level")
    audit_compliance: str = Field(..., description="Audit compliance status")
    fallback_resilience: str = Field(..., description="Fallback resilience level")


class ModelCredentialsAnalysis(BaseModel):
    """Credentials strength analysis results."""

    strength_score: int = Field(..., description="Overall strength score (0-100)")
    password_entropy: float | None = Field(
        None,
        description="Password entropy score",
    )
    common_patterns: list[str] = Field(
        default_factory=list,
        description="Detected common patterns",
    )
    security_issues: list[str] = Field(
        default_factory=list,
        description="Identified security issues",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Improvement recommendations",
    )
    compliance_status: str = Field(..., description="Compliance status")
    risk_level: str = Field(..., description="Risk assessment level")
    manager_assessment: ModelManagerAssessment = Field(
        ...,
        description="Manager-specific assessment",
    )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for current standards."""
        # Custom dictionary format for credentials analysis
        return {
            "strength_score": self.strength_score,
            "password_entropy": self.password_entropy,
            "common_patterns": self.common_patterns,
            "security_issues": self.security_issues,
            "recommendations": self.recommendations,
            "compliance_status": self.compliance_status,
            "risk_level": self.risk_level,
            "manager_assessment": {
                "backend_security_level": self.manager_assessment.backend_security_level,
                "audit_compliance": self.manager_assessment.audit_compliance,
                "fallback_resilience": self.manager_assessment.fallback_resilience,
            },
        }
