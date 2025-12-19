"""
Shape Validation Result Model.

Model for aggregated results of validating multiple execution shapes.
This model provides summary statistics and detailed results when validating
an entire system or component against ONEX canonical execution shapes.

See Also:
    - ModelExecutionShapeValidation: Individual validation results
    - EnumExecutionShape: Defines the canonical shapes
    - CANONICAL_EXECUTION_SHAPES.md: Full documentation of allowed/forbidden patterns
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
    shapes, providing summary statistics and detailed results. Use the
    `from_validations` factory method to create instances from a list
    of individual validation results.

    Attributes:
        validations: List of individual validation results
        total_validated: Total number of shapes that were validated
        allowed_count: Number of shapes that conform to canonical patterns
        disallowed_count: Number of shapes that violate canonical patterns
        is_fully_compliant: True if all validated shapes are allowed
        errors: List of error messages for disallowed shapes
        warnings: List of warning messages (e.g., deprecated patterns)

    Example:
        >>> from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
        >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
        >>> # Validate multiple shapes at once
        >>> validations = [
        ...     ModelExecutionShapeValidation.validate_shape(
        ...         EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
        ...     ),
        ...     ModelExecutionShapeValidation.validate_shape(
        ...         EnumMessageCategory.COMMAND, EnumNodeKind.REDUCER  # Invalid!
        ...     ),
        ... ]
        >>> result = ModelShapeValidationResult.from_validations(validations)
        >>> result.is_fully_compliant
        False
        >>> result.allowed_count
        1
        >>> result.disallowed_count
        1
        >>> len(result.errors)
        1
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

        This factory method aggregates multiple individual validation results
        into a single summary. It automatically computes counts, compliance
        status, and collects error messages from disallowed shapes.

        Args:
            validations: List of individual validation results from
                ModelExecutionShapeValidation.validate_shape()

        Returns:
            An aggregated ModelShapeValidationResult with summary statistics
            and the original validation details

        Example:
            >>> from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
            >>> from omnibase_core.enums.enum_node_kind import EnumNodeKind
            >>> validations = [
            ...     ModelExecutionShapeValidation.validate_shape(
            ...         EnumMessageCategory.EVENT, EnumNodeKind.ORCHESTRATOR
            ...     ),
            ...     ModelExecutionShapeValidation.validate_shape(
            ...         EnumMessageCategory.EVENT, EnumNodeKind.REDUCER
            ...     ),
            ... ]
            >>> result = ModelShapeValidationResult.from_validations(validations)
            >>> result.is_fully_compliant
            True
            >>> result.total_validated
            2
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
