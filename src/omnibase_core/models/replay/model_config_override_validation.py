"""
Validation result for configuration overrides.

This module provides the ModelConfigOverrideValidation model which represents
validation results for config overrides, checking path existence, type
compatibility, and override consistency.

Design:
    ModelConfigOverrideValidation follows the violations/warnings/suggestions
    pattern used by ServiceContractValidator and other validation components
    in the codebase. This provides a consistent interface for reporting
    validation outcomes with graduated severity levels.

    - **Violations**: Critical errors that must be fixed
    - **Warnings**: Non-critical issues that should be addressed
    - **Suggestions**: Optional improvements for better practices

Architecture:
    The validation model is used by config override injection to validate
    override specifications before applying them to execution contexts::

        ConfigOverrideInjector
            |
            +-- validate_overrides()
                    -> ModelConfigOverrideValidation
                            is_valid: bool
                            violations: tuple[str, ...]
                            warnings: tuple[str, ...]
                            suggestions: tuple[str, ...]

Thread Safety:
    ModelConfigOverrideValidation is frozen (immutable) after creation,
    making it safe to share across threads. All fields use immutable
    tuple types for collections.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelConfigOverrideValidation

        # Valid result
        result = ModelConfigOverrideValidation(
            is_valid=True,
            paths_validated=5,
            type_checks_passed=5,
        )

        # Invalid result with violations
        result = ModelConfigOverrideValidation(
            is_valid=False,
            violations=(
                "Path 'config.missing' does not exist",
                "Type mismatch: expected int, got str",
            ),
            warnings=("Config value 'timeout' is unusually high",),
            paths_validated=5,
            type_checks_passed=3,
        )

Related:
    - OMN-1205: Configuration Override Injection
    - ServiceContractValidator: Uses same violations/warnings/suggestions pattern
    - ModelReplayContext: Companion model for replay infrastructure

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelConfigOverrideValidation(BaseModel):
    """
    Validation result for a set of config overrides.

    Checks path existence, type compatibility, and override consistency.
    Follows the violations/warnings/suggestions pattern from ServiceContractValidator.

    Attributes:
        is_valid: Whether all overrides are valid (no violations).
        violations: Critical validation errors that must be fixed.
        warnings: Non-critical issues that should be addressed.
        suggestions: Improvement recommendations (optional to fix).
        paths_validated: Number of configuration paths checked.
        type_checks_passed: Number of type compatibility checks passed.

    Thread Safety:
        Immutable (frozen=True) after creation - thread-safe for concurrent reads.

    Example:
        Creating a valid result::

            result = ModelConfigOverrideValidation(
                is_valid=True,
                paths_validated=10,
                type_checks_passed=10,
            )

        Creating an invalid result::

            result = ModelConfigOverrideValidation(
                is_valid=False,
                violations=("Path 'x.y' not found",),
                warnings=("Value exceeds recommended range",),
                paths_validated=10,
                type_checks_passed=8,
            )

    .. versionadded:: 0.4.0
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    is_valid: bool = Field(..., description="Whether all overrides are valid")
    violations: tuple[str, ...] = Field(
        default_factory=tuple, description="Critical validation errors"
    )
    warnings: tuple[str, ...] = Field(
        default_factory=tuple, description="Non-critical issues"
    )
    suggestions: tuple[str, ...] = Field(
        default_factory=tuple, description="Improvement recommendations"
    )
    paths_validated: int = Field(default=0, description="Number of paths checked")
    type_checks_passed: int = Field(
        default=0, description="Number of type checks passed"
    )


__all__ = ["ModelConfigOverrideValidation"]
