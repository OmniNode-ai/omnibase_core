"""
Security Summary Model.

Comprehensive security summary for reporting with component summaries.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.security.model_authorization_summary import (
        ModelAuthorizationSummary,
    )
    from omnibase_core.models.security.model_compliance_summary import (
        ModelComplianceSummary,
    )
    from omnibase_core.models.security.model_security_event_summary import (
        ModelSecurityEventSummary,
    )
    from omnibase_core.models.security.model_signature_chain_summary import (
        ModelSignatureChainSummary,
    )


class ModelSecuritySummary(BaseModel):
    """Comprehensive security summary for reporting."""

    envelope_id: str = Field(..., description="Envelope identifier")
    security_level: str = Field(..., description="Required security level")
    is_encrypted: bool = Field(..., description="Whether payload is encrypted")
    signature_required: bool = Field(..., description="Whether signatures are required")
    content_hash: str = Field(..., description="Content hash for integrity")
    signature_chain: "ModelSignatureChainSummary" = Field(
        ...,
        description="Signature chain summary",
    )
    compliance: "ModelComplianceSummary" = Field(
        ...,
        description="Compliance information",
    )
    authorization: "ModelAuthorizationSummary" = Field(
        ...,
        description="Authorization requirements",
    )
    security_events_count: int = Field(..., description="Number of security events")
    last_security_event: "ModelSecurityEventSummary" | None = Field(
        None,
        description="Most recent security event",
    )

    def get_security_score(self) -> float:
        """Calculate overall security score (0-100)."""
        score = 50  # Base score

        # Encryption bonus
        if self.is_encrypted:
            score += 20

        # Signature validation bonus
        if self.signature_chain.is_valid():
            score += 15
        if self.signature_chain.is_trusted():
            score += 10

        # Compliance bonus
        if self.compliance.get_data_risk_level() == "low":
            score += 5

        # Authorization bonus
        if self.authorization.get_clearance_level() != "none":
            score += 5

        return min(score, 100)

    def get_risk_level(self) -> str:
        """Get overall risk level."""
        if self.get_security_score() >= 80:
            return "low"
        elif self.get_security_score() >= 60:
            return "medium"
        else:
            return "high"

    def has_recent_security_events(self, minutes_threshold: int = 60) -> bool:
        """Check if there are recent security events."""
        if self.last_security_event is None:
            return False
        return self.last_security_event.is_recent(minutes_threshold)

    def get_security_controls(self) -> dict[str, Any]:
        """Get security controls summary."""
        return {
            "encryption_enabled": self.is_encrypted,
            "signatures_required": self.signature_required,
            "signature_valid": self.signature_chain.is_valid(),
            "signature_trusted": self.signature_chain.is_trusted(),
            "has_recent_events": self.has_recent_security_events(),
            "security_events_count": self.security_events_count,
        }

    def get_comprehensive_summary(self) -> dict[str, Any]:
        """Get comprehensive security summary."""
        return {
            "envelope_id": self.envelope_id,
            "security_level": self.security_level,
            "security_score": self.get_security_score(),
            "risk_level": self.get_risk_level(),
            "controls": self.get_security_controls(),
            "signature_chain": self.signature_chain.get_chain_summary(),
            "compliance": self.compliance.get_summary(),
            "authorization": self.authorization.get_authorization_summary(),
            "last_security_event": (
                self.last_security_event.get_event_summary()
                if self.last_security_event
                else None
            ),
        }

    def validate_security_posture(self) -> dict[str, Any]:
        """Validate overall security posture."""
        issues = []

        if not self.is_encrypted:
            issues.append("Content is not encrypted")

        if not self.signature_chain.is_valid():
            issues.append("Signature chain is not valid")

        if not self.signature_chain.is_trusted():
            issues.append("Signature chain is not trusted")

        if self.has_recent_security_events():
            issues.append("Recent security events detected")

        if self.compliance.get_data_risk_level() == "high":
            issues.append("High risk data classification")

        return {
            "is_secure": len(issues) == 0,
            "issue_count": len(issues),
            "issues": issues,
            "security_score": self.get_security_score(),
        }
