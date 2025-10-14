"""
Contract validation result model.

Provides validation result with scoring and actionable feedback for autonomous
code generation systems.
"""

from pydantic import BaseModel, Field

from omnibase_core.primitives.model_semver import ModelSemVer


class ModelContractValidationResult(BaseModel):
    """
    Validation result with scoring and actionable feedback.

    Attributes:
        is_valid: Whether the contract passes all validation checks
        score: Validation score from 0.0 to 1.0
        violations: Critical errors that prevent validation
        warnings: Non-critical issues that should be addressed
        suggestions: Recommendations for improvement
        contract_type: Type of contract validated (effect, compute, etc.)
        interface_version: INTERFACE_VERSION used for validation
    """

    is_valid: bool = Field(
        ...,
        description="Whether the contract passes all validation checks",
    )

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Validation score from 0.0 to 1.0",
    )

    violations: list[str] = Field(
        default_factory=list,
        description="Critical errors that prevent validation",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Non-critical issues that should be addressed",
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="Recommendations for improvement",
    )

    contract_type: str | None = Field(
        default=None,
        description="Type of contract validated",
    )

    interface_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="INTERFACE_VERSION used for validation",
    )
