"""
ExceptionProtocolParsing Exception

Raised when Python AST parsing fails on a protocol file.

This is a specific subtype of ExceptionFileProcessing for syntax
errors or malformed Python code in protocol files.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.exceptions (hierarchy parent)
"""

from .exception_file_processing_error import ExceptionFileProcessingError


class ExceptionProtocolParsingError(ExceptionFileProcessingError):
    """
    Raised when Python AST parsing fails on a protocol file.

    This is a specific subtype of FileProcessingError for syntax
    errors or malformed Python code in protocol files.
    """
