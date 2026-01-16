"""
Centralized Exception Type Groups for ONEX.

This module provides standardized exception type tuples for consistent
error handling across the codebase. All tuples are alphabetically ordered
by exception class name.

Comment Markers (use in except blocks):
    # fallback-ok: Intentional catch-all for graceful degradation
    # catch-all-ok: Boundary handler that must not crash
    # cleanup-resilience-ok: Cleanup that must complete even on error
    # boundary-ok: API/system boundary handler
    # init-errors-ok: Initialization that provides defaults on failure
    # tool-resilience-ok: Tool/plugin that must not crash host

Usage:
    >>> from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
    >>>
    >>> try:
    ...     result = model.model_validate(data)
    ... except VALIDATION_ERRORS as e:
    ...     # Handle validation failure
    ...     pass

See Also:
    - docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md
    - CLAUDE.md section on exception handling
"""

import asyncio
import json

from pydantic import ValidationError

__all__ = [
    "ASYNC_ERRORS",
    "ATTRIBUTE_ACCESS_ERRORS",
    "FILE_IO_ERRORS",
    "JSON_PARSING_ERRORS",
    "NETWORK_ERRORS",
    "PYDANTIC_MODEL_ERRORS",
    "VALIDATION_ERRORS",
    "YAML_PARSING_ERRORS",
]

# =============================================================================
# Validation Exception Groups
# =============================================================================

# Standard validation errors for type checking and value validation
# Use when validating user input, configuration, or data transformations
VALIDATION_ERRORS: tuple[type[Exception], ...] = (
    TypeError,
    ValidationError,
    ValueError,
)

# Pydantic model validation errors (includes attribute access)
# Use when calling model_validate(), model_dump(), or accessing model fields
PYDANTIC_MODEL_ERRORS: tuple[type[Exception], ...] = (
    AttributeError,
    TypeError,
    ValidationError,
    ValueError,
)

# Attribute/key access errors
# Use when accessing dict keys, object attributes, or list indices
ATTRIBUTE_ACCESS_ERRORS: tuple[type[Exception], ...] = (
    AttributeError,
    IndexError,
    KeyError,
    TypeError,
)

# =============================================================================
# Parsing Exception Groups
# =============================================================================

# YAML parsing errors
# Use when parsing YAML configuration or contract files
try:
    import yaml

    YAML_PARSING_ERRORS: tuple[type[Exception], ...] = (
        ValidationError,
        ValueError,
        yaml.YAMLError,
    )
except ImportError:
    # yaml not available, provide fallback
    YAML_PARSING_ERRORS = (
        ValidationError,
        ValueError,
    )

# JSON parsing errors
# Use when parsing JSON data or API responses
JSON_PARSING_ERRORS: tuple[type[Exception], ...] = (
    json.JSONDecodeError,
    TypeError,
    ValidationError,
    ValueError,
)

# =============================================================================
# I/O Exception Groups
# =============================================================================

# File I/O errors
# Use when reading/writing files, checking paths, or file operations
FILE_IO_ERRORS: tuple[type[Exception], ...] = (
    FileNotFoundError,
    IOError,
    OSError,
    PermissionError,
)

# Network/connection errors
# Use when making HTTP requests, socket connections, or remote calls
NETWORK_ERRORS: tuple[type[Exception], ...] = (
    ConnectionError,
    OSError,
    TimeoutError,
)

# =============================================================================
# Async Exception Groups
# =============================================================================

# Async operation errors (excluding CancelledError which should propagate)
# Use when handling async task failures
ASYNC_ERRORS: tuple[type[Exception], ...] = (
    asyncio.TimeoutError,
    RuntimeError,
)

# Note: asyncio.CancelledError should NOT be in a catch tuple
# It must be caught separately and re-raised to honor task cancellation:
#
#     except asyncio.CancelledError:
#         # Cleanup if needed
#         raise  # Always re-raise!
