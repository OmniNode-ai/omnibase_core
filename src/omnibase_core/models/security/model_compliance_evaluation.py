"""
Compliance Evaluation Model.

Compliance evaluation result model for security framework validation.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelComplianceEvaluation(BaseModel):
    """Compliance evaluation result model."""

    status: dict[str, bool] = Field(
        default_factory=dict,
        description="Compliance framework status",
    )
    violations: list[str] = Field(
        default_factory=list,
        description="Compliance violations found",
    )
    warnings: list[str] = Field(default_factory=list, description="Compliance warnings")
    meets_requirements: bool = Field(
        default=False,
        description="Whether compliance requirements are met",
    )

    model_config = {
        "extra": "forbid",
        "frozen": True,
        "validate_assignment": True,
    }

    def add_violation(self, violation: str) -> "ModelComplianceEvaluation":
        """Add a violation to the evaluation."""
        new_violations = [*self.violations, violation]
        return self.model_copy(update={"violations": new_violations})

    def add_warning(self, warning: str) -> "ModelComplianceEvaluation":
        """Add a warning to the evaluation."""
        new_warnings = [*self.warnings, warning]
        return self.model_copy(update={"warnings": new_warnings})

    def update_status(self, key: str, value: bool) -> "ModelComplianceEvaluation":
        """Update compliance status for a specific framework."""
        new_status = {**self.status, key: value}
        return self.model_copy(update={"status": new_status})

    def is_compliant(self) -> bool:
        """Check if all requirements are met (no violations)."""
        return self.meets_requirements and len(self.violations) == 0

    def get_status_summary(self) -> dict[str, Any]:
        """Get compliance status summary."""
        return {
            "meets_requirements": self.meets_requirements,
            "violation_count": len(self.violations),
            "warning_count": len(self.warnings),
            "framework_count": len(self.status),
            "compliant_frameworks": sum(
                1 for compliant in self.status.values() if compliant
            ),
        }
