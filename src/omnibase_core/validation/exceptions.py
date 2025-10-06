"""
Custom exceptions for the validation framework.

These exceptions provide clear, specific error types for different failure modes
in protocol validation, auditing, and migration operations.
"""

# Import all exception classes from their individual files
from .exception_audit_error import AuditError
from .exception_configuration_error import ConfigurationError
from .exception_file_processing_error import FileProcessingError
from .exception_input_validation_error import InputValidationError
from .exception_migration_error import MigrationError
from .exception_path_traversal_error import PathTraversalError
from .exception_protocol_parsing_error import ProtocolParsingError
from .exception_validation_framework_error import ValidationFrameworkError

# Export all exceptions for convenient importing
__all__ = [
    "ValidationFrameworkError",
    "ConfigurationError",
    "FileProcessingError",
    "ProtocolParsingError",
    "AuditError",
    "MigrationError",
    "InputValidationError",
    "PathTraversalError",
]
