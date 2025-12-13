"""
Compliance Summary Model.

Compliance information summary with data classification indicators.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.security.model_security_summaries import (
    ModelComplianceInfoSummary,
)


class ModelComplianceSummary(BaseModel):
    """Compliance information summary."""

    frameworks: list[str] = Field(
        default=..., description="Applicable compliance frameworks"
    )
    classification: str = Field(default=..., description="Data classification level")
    contains_pii: bool = Field(
        default=...,
        description="Contains personally identifiable information",
    )
    contains_phi: bool = Field(
        default=..., description="Contains protected health information"
    )
    contains_financial: bool = Field(default=..., description="Contains financial data")

    def get_framework_count(self) -> int:
        """Get number of compliance frameworks."""
        return len(self.frameworks)

    def get_frameworks_by_type(self, framework_type: str) -> list[str]:
        """Get frameworks of a specific type."""
        return [f for f in self.frameworks if framework_type.lower() in f.lower()]

    def has_sensitive_data(self) -> bool:
        """Check if contains any sensitive data types."""
        return self.contains_pii or self.contains_phi or self.contains_financial

    def get_data_risk_level(self) -> str:
        """Get data risk level based on classification and content."""
        if self.has_sensitive_data() and self.classification in ["high", "critical"]:
            return "high"
        elif self.has_sensitive_data():
            return "medium"
        else:
            return "low"

    def get_summary(self) -> ModelComplianceInfoSummary:
        """Get compliance summary."""
        return ModelComplianceInfoSummary(
            framework_count=self.get_framework_count(),
            classification=self.classification,
            has_pii=self.contains_pii,
            has_phi=self.contains_phi,
            has_financial=self.contains_financial,
            has_sensitive_data=self.has_sensitive_data(),
            risk_level=self.get_data_risk_level(),
        )
