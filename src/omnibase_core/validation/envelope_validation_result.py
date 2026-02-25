# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnvelopeValidationResult - Result of envelope validation.

Contains the outcome of envelope validation including is_valid status,
error messages, warnings, and the validation mode used.

Related:
    - OMN-840: Add configurable validation strictness levels
    - EnvelopeValidator: Produces EnvelopeValidationResult instances
    - ModelEnvelopeValidationConfig: Configuration that determines validation behavior
"""

from __future__ import annotations

from dataclasses import dataclass, field

from omnibase_core.enums.enum_pipeline_validation_mode import EnumPipelineValidationMode

__all__ = ["EnvelopeValidationResult"]


@dataclass
class EnvelopeValidationResult:
    """
    Result of envelope validation.

    Returned by EnvelopeValidator.validate(). In strict mode, this is only
    returned when validation passes (failures raise EnvelopeValidationError).
    In lenient mode, this is always returned, with issues captured in errors
    and warnings.

    Attributes:
        is_valid: True if validation passed with no blocking errors.
        errors: List of error messages. Empty when is_valid is True.
            In lenient mode, errors can be non-empty while is_valid is False.
        warnings: List of warning messages. May be non-empty even when is_valid
            is True (e.g., type coercion warnings, missing optional fields).
        mode: The validation mode (STRICT or LENIENT) used for this validation.

    Example:
        >>> result = validator.validate(envelope)
        >>> if not result.is_valid:
        ...     for error in result.errors:
        ...         print(f"ERROR: {error}")
        >>> for warning in result.warnings:
        ...     print(f"WARN: {warning}")
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mode: EnumPipelineValidationMode = EnumPipelineValidationMode.LENIENT

    def has_errors(self) -> bool:
        """
        Return True if there are validation errors.

        Returns:
            True if the errors list is non-empty.
        """
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """
        Return True if there are validation warnings.

        Returns:
            True if the warnings list is non-empty.
        """
        return len(self.warnings) > 0
