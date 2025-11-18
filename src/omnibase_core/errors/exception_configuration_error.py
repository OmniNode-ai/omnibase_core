"""
ExceptionConfiguration Exception

Raised for invalid configuration, such as incorrect paths or missing dependencies.

This implements fail-fast behavior for setup issues that prevent
the validation framework from operating correctly.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.exceptions (hierarchy parent)
"""

from .exception_validation_framework_error import ExceptionValidationFrameworkError


class ExceptionConfigurationError(ExceptionValidationFrameworkError):
    """
    Raised for invalid configuration, such as incorrect paths or missing dependencies.

    This implements fail-fast behavior for setup issues that prevent
    the validation framework from operating correctly.
    """
