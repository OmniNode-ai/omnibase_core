"""
AuditError Exception

Raised for logical errors encountered during an audit.

This covers issues like inconsistent protocol state,
duplicate detection failures, or validation rule violations.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.validation.exceptions (hierarchy parent)
"""

from .exception_validation_framework_error import ValidationFrameworkError


class AuditError(ValidationFrameworkError):
    """
    Raised for logical errors encountered during an audit.

    This covers issues like inconsistent protocol state,
    duplicate detection failures, or validation rule violations.
    """
