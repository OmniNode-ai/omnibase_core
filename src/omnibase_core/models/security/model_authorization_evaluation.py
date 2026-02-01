"""
Authorization Evaluation Model.

Authorization evaluation result model for security access control validation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.security.model_security_summaries import (
    ModelAuthorizationEvaluationSummary,
)


class ModelAuthorizationEvaluation(BaseModel):
    """Authorization evaluation result model."""

    violations: list[str] = Field(
        default_factory=list,
        description="Authorization violations found",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Authorization warnings",
    )
    meets_requirements: bool = Field(
        default=False,
        description="Whether authorization requirements are met",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        validate_assignment=True,
    )

    def add_violation(self, violation: str) -> "ModelAuthorizationEvaluation":
        """Add a violation to the evaluation."""
        new_violations = [*self.violations, violation]
        return self.model_copy(update={"violations": new_violations})

    def add_warning(self, warning: str) -> "ModelAuthorizationEvaluation":
        """Add a warning to the evaluation."""
        new_warnings = [*self.warnings, warning]
        return self.model_copy(update={"warnings": new_warnings})

    def is_authorized(self) -> bool:
        """Check if authorization requirements are met (no violations)."""
        return self.meets_requirements and len(self.violations) == 0

    def get_summary(self) -> ModelAuthorizationEvaluationSummary:
        """Get authorization evaluation summary."""
        return ModelAuthorizationEvaluationSummary(
            meets_requirements=self.meets_requirements,
            violation_count=len(self.violations),
            warning_count=len(self.warnings),
            is_authorized=self.is_authorized(),
        )
