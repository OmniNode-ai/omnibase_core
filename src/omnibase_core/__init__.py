"""
Omnibase Core - ONEX Four-Node Architecture Implementation

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

# Import validation functions at package level for easy access
from .validation import (
    ValidationResult,
    ValidationSuite,
    validate_all,
    validate_architecture,
    validate_contracts,
    validate_patterns,
    validate_union_usage,
)

__all__ = [
    # Validation tools (main exports for other repositories)
    "validate_architecture",
    "validate_union_usage",
    "validate_contracts",
    "validate_patterns",
    "validate_all",
    "ValidationResult",
    "ValidationSuite",
]
