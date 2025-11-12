"""
ExceptionValidationFrameworkError Exception

Base exception for all validation framework errors.

This is the root exception class for the validation framework hierarchy,
providing a consistent base for all validation-related errors.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""


class ExceptionValidationFrameworkError(Exception):
    """Base exception for all validation framework errors."""
