"""
Shape Validation Result Model.

Model for aggregated results of validating multiple execution shapes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_execution_shape_validation import (
    ModelExecutionShapeValidation,
)

__all__ = [
    "ModelShapeValidationResult",
]


class ModelShapeValidationResult(BaseModel):
    """
    Aggregated result of validating multiple execution shapes.

    This model collects the results of validating multiple execution
    shapes, providing summary statistics and detailed results.

    Example:
        >>> result = ModelShapeValidationResult(
        ...     validations=[validation1, validation2],
        ...     total_validated=2,
        ...     allowed_count=1,
        ...     disallowed_count=1,
        ...     is_fully_compliant=False,
        ... )
        >>> result.is_fully_compliant
        False
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    validations: list[ModelExecutionShapeValidation] = Field(
        default_factory=list,
        description="List of individual shape validation results",
    )
    total_validated: int = Field(
        default=0,
        description="Total number of shapes validated",
    )
    allowed_count: int = Field(
        default=0,
        description="Number of shapes that are allowed",
    )
    disallowed_count: int = Field(
        default=0,
        description="Number of shapes that are disallowed",
    )
    is_fully_compliant: bool = Field(
        default=True,
        description="Whether all validated shapes are allowed",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages for disallowed shapes",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning messages",
    )

    @classmethod
    def from_validations(
        cls,
        validations: list[ModelExecutionShapeValidation],
    ) -> "ModelShapeValidationResult":
        """
        Create a result from a list of validations.

        Args:
            validations: List of individual validation results

        Returns:
            An aggregated ModelShapeValidationResult
        """
        allowed = [v for v in validations if v.is_allowed]
        disallowed = [v for v in validations if not v.is_allowed]
        errors = [v.rationale for v in disallowed]

        return cls(
            validations=validations,
            total_validated=len(validations),
            allowed_count=len(allowed),
            disallowed_count=len(disallowed),
            is_fully_compliant=len(disallowed) == 0,
            errors=errors,
        )
