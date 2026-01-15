"""
Custom exceptions for the validation framework.

These exceptions provide clear, specific error types for different failure modes
in protocol validation, auditing, and migration operations.
"""

# Import all exception classes from their individual files
from .exception_audit_error import ExceptionAuditError
from .exception_configuration_error import ExceptionConfigurationError
from .exception_file_processing_error import ExceptionFileProcessingError
from .exception_input_validation_error import ExceptionInputValidationError
from .exception_migration_error import ExceptionMigrationError
from .exception_path_traversal_error import ExceptionPathTraversalError
from .exception_protocol_parsing_error import ExceptionProtocolParsingError
from .exception_validation_framework_error import ExceptionValidationFrameworkError

# Export all exceptions for convenient importing
__all__ = [
    "ExceptionValidationFrameworkError",
    "ExceptionConfigurationError",
    "ExceptionFileProcessingError",
    "ExceptionProtocolParsingError",
    "ExceptionAuditError",
    "ExceptionMigrationError",
    "ExceptionInputValidationError",
    "ExceptionPathTraversalError",
]
