"""
Custom exceptions for the validation framework.

These exceptions provide clear, specific error types for different failure modes
in protocol validation, auditing, and migration operations.
"""


class ValidationFrameworkError(Exception):
    """Base exception for all validation framework errors."""

    pass


class ConfigurationError(ValidationFrameworkError):
    """
    Raised for invalid configuration, such as incorrect paths or missing dependencies.

    This implements fail-fast behavior for setup issues that prevent
    the validation framework from operating correctly.
    """

    pass


class FileProcessingError(ValidationFrameworkError):
    """
    Raised when a file cannot be read or parsed.

    Carries context about the file path and specific error details
    to aid in debugging protocol processing issues.
    """

    def __init__(
        self, message: str, file_path: str, original_exception: Exception | None = None
    ) -> None:
        self.file_path = file_path
        self.original_exception = original_exception
        super().__init__(f"{message} [File: {self.file_path}]")


class ProtocolParsingError(FileProcessingError):
    """
    Raised when Python AST parsing fails on a protocol file.

    This is a specific subtype of FileProcessingError for syntax
    errors or malformed Python code in protocol files.
    """

    pass


class AuditError(ValidationFrameworkError):
    """
    Raised for logical errors encountered during an audit.

    This covers issues like inconsistent protocol state,
    duplicate detection failures, or validation rule violations.
    """

    pass


class MigrationError(ValidationFrameworkError):
    """
    Raised for errors during protocol migration operations.

    This covers file system operations, conflict resolution,
    and rollback scenarios during protocol migration.
    """

    pass


class InputValidationError(ValidationFrameworkError):
    """
    Raised when input parameters fail validation checks.

    This implements security best practices by validating
    all user-provided inputs before processing.
    """

    pass


class PathTraversalError(InputValidationError):
    """
    Raised when a path would result in directory traversal outside allowed directories.

    This prevents security vulnerabilities from malicious or malformed paths.
    """

    pass
