# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
EnvelopeValidationError - Exception raised when envelope validation fails in strict mode.

This exception is raised by EnvelopeValidator when an envelope fails structural
or payload validation in strict mode.

Related:
    - OMN-840: Add configurable validation strictness levels
    - EnvelopeValidator: Raises this exception on strict mode failures
    - ModelEnvelopeValidationConfig: Configures strict vs lenient mode
"""

from __future__ import annotations

__all__ = ["EnvelopeValidationError"]


class EnvelopeValidationError(Exception):
    """
    Raised when envelope validation fails in strict mode.

    Contains the list of validation errors that caused the failure.

    Attributes:
        errors: List of human-readable error messages.
        envelope_id: The envelope ID that failed validation (if available).

    Example:
        >>> try:
        ...     validator.validate(malformed_envelope)
        ... except EnvelopeValidationError as e:
        ...     for error in e.errors:
        ...         print(f"Validation error: {error}")
    """

    def __init__(self, errors: list[str], envelope_id: str | None = None) -> None:
        """
        Initialize with error details.

        Args:
            errors: List of human-readable error messages describing validation failures.
            envelope_id: The envelope ID that failed validation, for debugging.
        """
        self.errors = errors
        self.envelope_id = envelope_id
        super().__init__(
            "Envelope validation failed"
            + (f" [{envelope_id}]" if envelope_id else "")
            + f": {'; '.join(errors)}"
        )
