from omnibase_core.errors.error_codes import ModelCoreErrorCode, ModelOnexError

"""
Omnibase Core - ONEX Four-Node ModelArchitecture Implementation

Main module for the omnibase_core package following ONEX standards.

This package provides:
- Core ONEX models and enums
- Validation tools for ONEX compliance
- Utilities for ONEX development

Validation Tools:
    The validation module provides comprehensive validation tools for ONEX compliance
    that can be used by other repositories in the omni* ecosystem.

    Quick usage:
        from omnibase_core.validation import validate_architecture, validate_union_usage

        # Validate architecture
        result = validate_architecture("src/")

        # Validate union usage
        result = validate_union_usage("src/", strict=True)

        # Run all validations
        from omnibase_core.validation import validate_all
        results = validate_all("src/")

    CLI usage:
        python -m omnibase_core.validation architecture src/
        python -m omnibase_core.validation union-usage --strict
        python -m omnibase_core.validation all
"""

from omnibase_core.errors import ModelCoreErrorCode, ModelOnexError

# No typing imports needed for lazy loading


# Lazy import validation functions to avoid import penalty
# Import validation functions only when accessed to improve startup performance
def __getattr__(name: str) -> object:
    if name in {
        "ValidationResult",
        "ModelValidationSuite",
        "validate_all",
        "validate_architecture",
        "validate_contracts",
        "validate_patterns",
        "validate_union_usage",
    }:
        from .validation import (
            ModelValidationSuite,
            ValidationResult,
            validate_all,
            validate_architecture,
            validate_contracts,
            validate_patterns,
            validate_union_usage,
        )

        # Return the requested attribute from validation module
        return locals()[name]
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise ModelOnexError(
        code=ModelCoreErrorCode.IMPORT_ERROR,
        message=msg,
        details={"module": __name__, "attribute": name},
    )


__all__ = [
    # Validation tools (main exports for other repositories)
    "ModelValidationSuite",
    "ValidationResult",
    "validate_all",
    "validate_architecture",
    "validate_contracts",
    "validate_patterns",
    "validate_union_usage",
]
