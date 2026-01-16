"""
Protocol for Constraint Validation Result.

Defines the expected interface for results returned by constraint validators.
This protocol enables duck typing for validation results while providing
clear documentation of the expected attributes.

Design Principles:
    - Protocol-first: Use typing.Protocol for interface definitions
    - Duck typing compatible: ModelValidationResult works without changes
    - Minimal interface: Only define attributes used by the pipeline

Related:
    - OMN-1128: Contract Validation Pipeline
    - ProtocolConstraintValidator: Returns this result type
    - ModelValidationResult: Compatible implementation

.. versionadded:: 0.4.1
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


__all__ = [
    "ProtocolConstraintValidationResult",
]


@runtime_checkable
class ProtocolConstraintValidationResult(Protocol):
    """Protocol interface for constraint validation results.

    Defines the minimum interface for results returned by constraint
    validators. Any object with these attributes can be used as a
    constraint validation result.

    Attributes:
        is_valid: True if validation passed with no critical errors.
        issues: List of all validation issues found.
        errors: List of error messages (subset of issues).
        warnings: List of warning messages (subset of issues).

    Note:
        ModelValidationResult already implements this interface.
        Custom implementations can use any class that has these
        attributes.

    Example:
        >>> class MyResult:
        ...     def __init__(self):
        ...         self.is_valid = True
        ...         self.issues = []
        ...         self.errors = []
        ...         self.warnings = []
        ...
        >>> result: ProtocolConstraintValidationResult = MyResult()
    """

    @property
    def is_valid(self) -> bool:
        """Whether the validation passed with no critical errors."""
        ...

    @property
    def issues(self) -> Sequence[ModelValidationIssue]:
        """All validation issues found during validation."""
        ...

    @property
    def errors(self) -> Sequence[str]:
        """Error messages from validation."""
        ...

    @property
    def warnings(self) -> Sequence[str]:
        """Warning messages from validation."""
        ...
