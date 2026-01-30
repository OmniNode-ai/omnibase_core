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

Validators:
    The validation module provides reusable validation tools that can be used
    by any project consuming omnibase_core as a dependency.

    Quick usage:
        from omnibase_core.validation import CircularImportValidator

        # Detect circular imports
        validator = CircularImportValidator(source_path="/path/to/src")
        result = validator.validate()
        if result.has_circular_imports:
            print(f"Found {len(result.circular_imports)} circular imports")
"""

# string-version-ok: Package metadata follows PEP 396 standard Python practice
__version__ = "0.9.11"


# =============================================================================
# Lazy loading: Avoid circular imports during module initialization.
# This defers imports of error classes and validation functions that would
# cause circular dependency chains if imported at module load time.
# =============================================================================
def __getattr__(name: str) -> object:
    """
    Lazy import to break circular dependency chains.

    Error classes (EnumCoreErrorCode, ModelOnexError) and validation functions
    are imported on first access rather than at module load time. This prevents
    circular imports that would occur if these heavily-imported modules were
    loaded eagerly.
    """
    # Import error classes lazily to break circular dependency
    if name == "EnumCoreErrorCode":
        from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

        return EnumCoreErrorCode
    if name == "ModelOnexError":
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        return ModelOnexError
    if name in {
        "ModelValidationResult",
        "ServiceValidationSuite",
        "validate_all",
        "validate_architecture",
        "validate_contracts",
        "validate_patterns",
        "validate_union_usage",
    }:
        from .validation import (  # noqa: F401
            ModelValidationResult,
            ServiceValidationSuite,
            validate_all,
            validate_architecture,
            validate_contracts,
            validate_patterns,
            validate_union_usage,
        )

        # Return the requested attribute from validation module
        return locals()[name]

    if name in {
        "CircularImportValidator",
        "CircularImportValidationResult",
        "EnumImportStatus",
        "ModelModuleImportResult",
    }:
        from .validation import (  # noqa: F401
            CircularImportValidationResult,
            CircularImportValidator,
            EnumImportStatus,
            ModelModuleImportResult,
        )

        # Return the requested attribute from validation module
        return locals()[name]

    # Import here to avoid circular dependency
    from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
    from omnibase_core.models.errors.model_onex_error import ModelOnexError

    msg = f"module '{__name__}' has no attribute '{name}'"
    raise ModelOnexError(
        error_code=EnumCoreErrorCode.IMPORT_ERROR,
        message=msg,
        details={"module": __name__, "attribute": name},
    )


__all__ = [
    # Error classes (commonly used)
    "EnumCoreErrorCode",
    "ModelOnexError",
    # Validation tools (main exports for other repositories)
    "ServiceValidationSuite",
    "ModelValidationResult",
    "validate_all",
    "validate_architecture",
    "validate_contracts",
    "validate_patterns",
    "validate_union_usage",
]
