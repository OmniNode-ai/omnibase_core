"""
ExceptionMigration Exception

Raised for errors during protocol migration operations.

This covers file system operations, conflict resolution,
and rollback scenarios during protocol migration.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.exceptions (hierarchy parent)
"""

from .exception_validation_framework_error import ExceptionValidationFrameworkError


class ExceptionMigrationError(ExceptionValidationFrameworkError):
    """
    Raised for errors during protocol migration operations.

    This covers file system operations, conflict resolution,
    and rollback scenarios during protocol migration.
    """
