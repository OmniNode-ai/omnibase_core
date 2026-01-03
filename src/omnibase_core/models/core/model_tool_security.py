"""
Tool Security Model.

Security configuration and requirements for tools.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_tool_security_assessment import (
    ModelToolSecurityAssessment,
)
from omnibase_core.models.core.model_tool_security_summary import (
    ModelToolSecuritySummary,
)


class ModelToolSecurity(BaseModel):
    """Security configuration and requirements."""

    processes_sensitive_data: bool = Field(
        default=False,
        description="Whether tool processes sensitive data",
    )
    data_classification: str = Field(
        default="internal",
        description="Data classification level",
    )
    requires_network_access: bool = Field(
        default=False,
        description="Whether tool requires network access",
    )
    external_endpoints: list[str] = Field(
        default_factory=list,
        description="External endpoints accessed",
    )
    security_profile_required: str = Field(
        default="SP0_BOOTSTRAP",
        description="Required security profile level",
    )

    def handles_sensitive_data(self) -> bool:
        """Check if tool handles sensitive data."""
        return self.processes_sensitive_data

    def is_network_required(self) -> bool:
        """Check if tool requires network access."""
        return self.requires_network_access

    def accesses_external_endpoints(self) -> bool:
        """Check if tool accesses external endpoints."""
        return len(self.external_endpoints) > 0

    def get_data_classification_level(self) -> str:
        """Get data classification level in lowercase."""
        return self.data_classification.lower()

    def get_security_profile_level(self) -> str:
        """Get security profile level."""
        return self.security_profile_required

    def is_high_security_profile(self) -> bool:
        """Check if tool requires high security profile."""
        return self.security_profile_required in [
            "SP2_PRODUCTION",
            "SP3_HIGH_ASSURANCE",
        ]

    def is_bootstrap_profile(self) -> bool:
        """Check if tool uses bootstrap security profile."""
        return self.security_profile_required == "SP0_BOOTSTRAP"

    def get_external_endpoint_count(self) -> int:
        """Get number of external endpoints."""
        return len(self.external_endpoints)

    def get_security_assessment(self) -> ModelToolSecurityAssessment:
        """Get security assessment summary."""
        risk_level = "low"
        if self.handles_sensitive_data() or self.is_high_security_profile():
            risk_level = "high"
        elif self.is_network_required() or self.accesses_external_endpoints():
            risk_level = "medium"

        return ModelToolSecurityAssessment(
            processes_sensitive_data=self.handles_sensitive_data(),
            requires_network_access=self.is_network_required(),
            accesses_external_endpoints=self.accesses_external_endpoints(),
            data_classification=self.get_data_classification_level(),
            security_profile=self.get_security_profile_level(),
            is_high_security=self.is_high_security_profile(),
            is_bootstrap=self.is_bootstrap_profile(),
            external_endpoint_count=self.get_external_endpoint_count(),
            risk_level=risk_level,
        )

    def get_summary(self) -> ModelToolSecuritySummary:
        """Get security configuration summary."""
        return ModelToolSecuritySummary(
            processes_sensitive_data=self.processes_sensitive_data,
            data_classification=self.data_classification,
            requires_network_access=self.requires_network_access,
            external_endpoints=self.external_endpoints,
            security_profile_required=self.security_profile_required,
            security_assessment=self.get_security_assessment(),
        )
