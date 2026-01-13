"""
Signature Evaluation Model.

Signature evaluation result model for security and compliance validation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.security.model_security_summaries import (
    ModelSignatureEvaluationSummary,
)


class ModelSignatureEvaluation(BaseModel):
    """Signature evaluation result model."""

    is_valid: bool = Field(
        default=False,
        description="Whether signature evaluation passed",
    )
    violations: list[str] = Field(
        default_factory=list,
        description="Signature violations found",
    )
    warnings: list[str] = Field(default_factory=list, description="Signature warnings")
    meets_requirements: bool = Field(
        default=False,
        description="Whether signature meets requirements",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
        validate_assignment=True,
    )

    def add_violation(self, violation: str) -> "ModelSignatureEvaluation":
        """Add a violation to the evaluation."""
        new_violations = [*self.violations, violation]
        return self.model_copy(update={"violations": new_violations})

    def add_warning(self, warning: str) -> "ModelSignatureEvaluation":
        """Add a warning to the evaluation."""
        new_warnings = [*self.warnings, warning]
        return self.model_copy(update={"warnings": new_warnings})

    def is_valid_signature(self) -> bool:
        """Check if signature is valid (no violations)."""
        return self.is_valid and len(self.violations) == 0

    def get_summary(self) -> ModelSignatureEvaluationSummary:
        """Get evaluation summary."""
        return ModelSignatureEvaluationSummary(
            is_valid=self.is_valid,
            meets_requirements=self.meets_requirements,
            violation_count=len(self.violations),
            warning_count=len(self.warnings),
        )
