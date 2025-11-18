"""
ExceptionFileProcessing Exception

Raised when a file cannot be read or parsed.

Carries context about the file path and specific error details
to aid in debugging protocol processing issues.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.exceptions (hierarchy parent)
"""

from .exception_validation_framework_error import ExceptionValidationFrameworkError


class ExceptionFileProcessingError(ExceptionValidationFrameworkError):
    """
    Raised when a file cannot be read or parsed.

    Carries context about the file path and specific error details
    to aid in debugging protocol processing issues.
    """

    def __init__(
        self,
        message: str,
        file_path: str,
        original_exception: Exception | None = None,
    ):
        self.file_path = file_path
        self.original_exception = original_exception
        super().__init__(f"{message} [File: {self.file_path}]")
