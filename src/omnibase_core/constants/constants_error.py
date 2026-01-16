"""Centralized error code constants and patterns.

This module provides the single source of truth for error code patterns
used throughout the ONEX system.

Error Code Format:
    Error codes must follow the CATEGORY_NNN pattern (e.g., AUTH_001,
    VALIDATION_123, SYSTEM_01). The format is validated using the regex
    pattern: ^[A-Z][A-Z0-9_]*_\\d{1,4}$

    For complete error code standards including valid/invalid examples,
    standard categories, and best practices, see:
    docs/conventions/ERROR_CODE_STANDARDS.md

Pattern Usage:
    This pattern is imported by:
    - omnibase_core.models.context.model_error_metadata
    - omnibase_core.models.context.model_retry_error_context
    - omnibase_core.validation.validators.validator_common

    The centralization avoids pattern drift and ensures consistent validation
    across all error handling code.

Thread Safety:
    Compiled regex patterns are immutable and thread-safe.

Example:
    >>> from omnibase_core.constants import ERROR_CODE_PATTERN
    >>> ERROR_CODE_PATTERN.match("AUTH_001")
    <re.Match object; span=(0, 8), match='AUTH_001'>
    >>> ERROR_CODE_PATTERN.match("auth_001")  # Invalid: lowercase
    None
"""

import re

__all__ = [
    "ERROR_CODE_PATTERN",
    "ERROR_CODE_PATTERN_STRING",
]

# Pattern string for documentation and external use
ERROR_CODE_PATTERN_STRING: str = r"^[A-Z][A-Z0-9_]*_\d{1,4}$"
"""Raw regex pattern string for error codes.

Use ERROR_CODE_PATTERN for matching; this string is for documentation
or when a string pattern is needed (e.g., JSON schema validation).
"""

# Compiled pattern for error codes: CATEGORY_NNN format
# - Valid: AUTH_001, VALIDATION_123, NETWORK_TIMEOUT_001, SYSTEM_01
# - Invalid: E001 (lint-style, no underscore), auth_001 (lowercase)
ERROR_CODE_PATTERN: re.Pattern[str] = re.compile(ERROR_CODE_PATTERN_STRING)
"""Compiled regex pattern for validating ONEX structured error codes.

Pattern: ^[A-Z][A-Z0-9_]*_\\d{1,4}$

This pattern enforces:
- Starts with uppercase letter [A-Z]
- Followed by uppercase letters, digits, or underscores [A-Z0-9_]*
- Underscore separator before numeric suffix _
- 1-4 digit numeric suffix \\d{1,4}

Examples:
    Valid: AUTH_001, VALIDATION_123, NETWORK_TIMEOUT_001, V2_AUTH_99
    Invalid: E001 (lint-style), auth_001 (lowercase), AUTH (no suffix)

Note:
    For lint-style short codes (W001, E001), use checker_workflow_linter module.
    Those follow a different pattern for workflow linting purposes.
"""
