"""
ExceptionPathTraversal Exception

Raised when a path would result in directory traversal outside allowed directories.

This prevents security vulnerabilities from malicious or malformed paths.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.exceptions (hierarchy parent)
"""

from .exception_input_validation_error import ExceptionInputValidationError


class ExceptionPathTraversalError(ExceptionInputValidationError):
    """
    Raised when a path would result in directory traversal outside allowed directories.

    This prevents security vulnerabilities from malicious or malformed paths.
    """
