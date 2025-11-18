"""
ExceptionInputValidation Exception

Raised when input parameters fail validation checks.

This implements security best practices by validating
all user-provided inputs before processing.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.exceptions (hierarchy parent)
"""

from .exception_validation_framework_error import ExceptionValidationFrameworkError


class ExceptionInputValidationError(ExceptionValidationFrameworkError):
    """
    Raised when input parameters fail validation checks.

    This implements security best practices by validating
    all user-provided inputs before processing.
    """
