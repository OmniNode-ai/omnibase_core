# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure name, identifier, and patch-list validation helpers.

These helpers were extracted from ``omnibase_core.validation.validator_utils``
under OMN-14331 (epic OMN-3210) so that domain MODELS can reuse them without
importing the ``validation`` behavioral layer — the ``models -> validation``
import back-edge the intra-core import-linter oracle forbids.

Every function here is pure (standard library only: ``re``, ``keyword``,
``logging``); nothing in this module imports ``omnibase_core.models`` or any
higher layer, so it sits cleanly below ``models``. ``validator_utils`` imports
and re-exports these names as part of the current validation API.

Error Handling
--------------
The Pydantic-oriented helpers (``validate_string_list``, ``validate_onex_name_list``)
raise ``ValueError`` because Pydantic ``@field_validator`` methods require it.
"""

from __future__ import annotations

import keyword
import logging
import re

# Configure logger for this module
logger = logging.getLogger(__name__)

# =============================================================================
# Pre-compiled Regex Patterns for Name Validation
# =============================================================================
# Thread-safe: patterns are compiled once at module load time and re.Pattern
# objects are immutable, allowing safe concurrent access.

# Pattern for validating Python identifier format (starts with letter/underscore,
# followed by alphanumeric/underscore)
_PYTHON_IDENTIFIER_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Pattern for validating ONEX naming convention (alphanumeric with underscores only)
_ONEX_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_]+$")

# Pattern for lowercase ONEX names (snake_case style)
_ONEX_LOWERCASE_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9_]+$")

# Characters that are dangerous in import paths (potential security issues)
_DANGEROUS_IMPORT_CHARS: frozenset[str] = frozenset(
    ["<", ">", "|", "&", ";", "`", "$", "'", '"', "*", "?", "[", "]"]
)


# =============================================================================
# Name and Identifier Validation Functions
# =============================================================================


def is_valid_python_identifier(name: str) -> bool:
    """Check if a string is a valid Python identifier.

    A valid Python identifier:
    - Starts with a letter (a-z, A-Z) or underscore (_)
    - Contains only letters, digits (0-9), or underscores
    - Is not empty

    This function uses a pre-compiled regex pattern for performance.

    Args:
        name: The string to validate.

    Returns:
        True if the string is a valid Python identifier, False otherwise.

    Example:
        >>> is_valid_python_identifier("my_var")
        True
        >>> is_valid_python_identifier("MyClass")
        True
        >>> is_valid_python_identifier("_private")
        True
        >>> is_valid_python_identifier("2fast")
        False
        >>> is_valid_python_identifier("my-var")
        False
    """
    if not name:
        logger.debug("Python identifier validation failed: empty name")
        return False
    is_valid = bool(_PYTHON_IDENTIFIER_PATTERN.match(name))
    logger.debug(f"Python identifier validation for {name!r}: {is_valid}")
    return is_valid


def is_valid_onex_name(name: str, *, lowercase_only: bool = False) -> bool:
    """Check if a string follows ONEX naming conventions.

    ONEX names must contain only alphanumeric characters and underscores.
    Optionally, names can be restricted to lowercase only (snake_case style).

    Args:
        name: The string to validate.
        lowercase_only: If True, requires all lowercase characters.

    Returns:
        True if the string follows ONEX naming conventions, False otherwise.

    Example:
        >>> is_valid_onex_name("http_client")
        True
        >>> is_valid_onex_name("HttpClient")
        True
        >>> is_valid_onex_name("http-client")
        False
        >>> is_valid_onex_name("HttpClient", lowercase_only=True)
        False
        >>> is_valid_onex_name("http_client", lowercase_only=True)
        True
    """
    if not name:
        logger.debug("ONEX name validation failed: empty name")
        return False
    if lowercase_only:
        is_valid = bool(_ONEX_LOWERCASE_NAME_PATTERN.match(name))
    else:
        is_valid = bool(_ONEX_NAME_PATTERN.match(name))
    logger.debug(
        f"ONEX name validation for {name!r} (lowercase_only={lowercase_only}): {is_valid}"
    )
    return is_valid


# =============================================================================
# Patch Validation Helper Functions
# =============================================================================


def validate_string_list(
    values: list[str] | None,
    field_name: str,
    *,
    min_length: int = 1,
    strip_whitespace: bool = True,
    reject_empty_list: bool = False,
    warn_empty_list: bool = False,
) -> list[str] | None:
    """Validate a list of strings, ensuring no empty values.

    This is a shared helper for Pydantic field validation that handles common
    string list validation patterns.

    Args:
        values: List of strings to validate, or None.
        field_name: Name of the field being validated (for error messages).
        min_length: Minimum length for each string after stripping.
        strip_whitespace: If True, strip whitespace from each value.
        reject_empty_list: If True, raise ValueError for empty lists.
            Use for add/remove operations where an empty list is likely a user error.
        warn_empty_list: If True, log a warning for empty lists but don't reject.
            Useful for detecting potential user errors without failing validation.

    Returns:
        Validated list of strings, or None if input was None.

    Raises:
        ValueError: If any string is empty or too short after processing,
            or if reject_empty_list is True and the list is empty.
            Note: This function raises ValueError (not ModelOnexError) because
            it is designed for use in Pydantic @field_validator methods, which
            require ValueError for validation failures.

    Example:
        >>> validate_string_list(["foo", "bar"], "events")
        ['foo', 'bar']
        >>> validate_string_list(["  foo  ", "bar"], "events")
        ['foo', 'bar']
        >>> validate_string_list(["", "bar"], "events")
        ValueError: events[0]: Value cannot be empty
        >>> validate_string_list([], "events", reject_empty_list=True)
        ValueError: events: List cannot be empty
    """
    if values is None:
        return None

    if len(values) == 0:
        if reject_empty_list:
            logger.debug(f"Validation failed for {field_name}: empty list rejected")
            # error-ok: Pydantic validators require ValueError
            raise ValueError(f"{field_name}: List cannot be empty")
        if warn_empty_list:
            logger.warning(
                f"Empty list provided for {field_name}. "
                "Consider omitting the field or providing values."
            )
        return values

    validated: list[str] = []
    for i, value in enumerate(values):
        if strip_whitespace:
            value = value.strip()

        if not value:
            logger.debug(f"Validation failed for {field_name}[{i}]: empty string")
            # error-ok: Pydantic validators require ValueError
            raise ValueError(f"{field_name}[{i}]: Value cannot be empty")

        if len(value) < min_length:
            logger.debug(
                f"Validation failed for {field_name}[{i}]: "
                f"value {value!r} is shorter than {min_length} characters"
            )
            # error-ok: Pydantic validators require ValueError
            raise ValueError(
                f"{field_name}[{i}]: Value must be at least {min_length} "
                f"characters: {value!r}"
            )

        validated.append(value)

    logger.debug(f"Validated {len(validated)} values for {field_name}")
    return validated


def validate_onex_name_list(
    values: list[str] | None,
    field_name: str,
    *,
    normalize_lowercase: bool = True,
    reject_empty_list: bool = False,
    warn_empty_list: bool = False,
) -> list[str] | None:
    """Validate a list of ONEX-compliant names.

    This is a shared helper for Pydantic field validation that validates names
    conform to ONEX naming conventions (alphanumeric + underscores).

    Args:
        values: List of names to validate, or None.
        field_name: Name of the field being validated (for error messages).
        normalize_lowercase: If True, normalize all names to lowercase.
        reject_empty_list: If True, raise ValueError for empty lists.
            Use for add/remove operations where an empty list is likely a user error.
        warn_empty_list: If True, log a warning for empty lists but don't reject.
            Useful for detecting potential user errors without failing validation.

    Returns:
        Validated and optionally normalized list of names, or None if input was None.

    Raises:
        ValueError: If any name is empty or contains invalid characters,
            or if reject_empty_list is True and the list is empty.
            Note: This function raises ValueError (not ModelOnexError) because
            it is designed for use in Pydantic @field_validator methods, which
            require ValueError for validation failures.

    Example:
        >>> validate_onex_name_list(["http_client", "kafka_producer"], "handlers")
        ['http_client', 'kafka_producer']
        >>> validate_onex_name_list(["HTTP_Client"], "handlers", normalize_lowercase=True)
        ['http_client']
        >>> validate_onex_name_list(["http-client"], "handlers")
        ValueError: handlers[0]: Name must contain only alphanumeric characters
        and underscores: 'http-client'
        >>> validate_onex_name_list([], "handlers", reject_empty_list=True)
        ValueError: handlers: List cannot be empty
    """
    if values is None:
        return None

    if len(values) == 0:
        if reject_empty_list:
            logger.debug(f"Validation failed for {field_name}: empty list rejected")
            # error-ok: Pydantic validators require ValueError
            raise ValueError(f"{field_name}: List cannot be empty")
        if warn_empty_list:
            logger.warning(
                f"Empty list provided for {field_name}. "
                "Consider omitting the field or providing values."
            )
        return values

    validated: list[str] = []
    for i, name in enumerate(values):
        name = name.strip()

        if not name:
            logger.debug(f"Validation failed for {field_name}[{i}]: empty name")
            # error-ok: Pydantic validators require ValueError
            raise ValueError(f"{field_name}[{i}]: Name cannot be empty")

        if not is_valid_onex_name(name):
            logger.debug(
                f"Validation failed for {field_name}[{i}]: invalid ONEX name {name!r}"
            )
            # error-ok: Pydantic validators require ValueError
            raise ValueError(
                f"{field_name}[{i}]: Name must contain only alphanumeric "
                f"characters and underscores: {name!r}"
            )

        if normalize_lowercase:
            name = name.lower()

        validated.append(name)

    logger.debug(f"Validated {len(validated)} ONEX names for {field_name}")
    return validated


def detect_add_remove_conflicts(
    add_values: list[str] | None,
    remove_values: list[str] | None,
    field_name: str,
    *,
    case_sensitive: bool = False,
    warn_empty_lists: bool = False,
) -> list[str]:
    """Detect conflicts between add and remove operations.

    A conflict occurs when the same value appears in both the add and
    remove lists, which would result in undefined or contradictory behavior.

    Uses O(n) set-based duplicate detection for efficient conflict checking.

    Args:
        add_values: Values being added (may be pre-normalized).
        remove_values: Values being removed (may be pre-normalized).
        field_name: Name of the field (for logging).
        case_sensitive: If True, compare values case-sensitively.
        warn_empty_lists: If True, log a warning when both lists are empty.
            Useful for detecting potential user errors in patch operations.

    Returns:
        List of conflicting values (empty if no conflicts).

    Example:
        >>> detect_add_remove_conflicts(
        ...     ["foo", "bar"], ["bar", "baz"], "handlers"
        ... )
        ['bar']
        >>> detect_add_remove_conflicts(
        ...     ["foo"], ["bar"], "handlers"
        ... )
        []
        >>> detect_add_remove_conflicts(
        ...     [], [], "handlers", warn_empty_lists=True
        ... )
        []  # Logs warning about empty lists
    """
    if add_values is None or remove_values is None:
        logger.debug(
            f"Skipping conflict detection for {field_name}: "
            f"add_values={add_values is not None}, remove_values={remove_values is not None}"
        )
        return []

    # Check for empty lists when both are provided
    if warn_empty_lists and len(add_values) == 0 and len(remove_values) == 0:
        logger.warning(
            f"Both add and remove lists are empty for {field_name}. "
            "This may indicate a user error in the patch definition."
        )

    # O(n) set-based conflict detection
    if case_sensitive:
        add_set = set(add_values)
        remove_set = set(remove_values)
    else:
        add_set = {v.lower() for v in add_values}
        remove_set = {v.lower() for v in remove_values}

    conflicts = sorted(add_set & remove_set)

    if conflicts:
        logger.warning(
            f"Detected {len(conflicts)} add/remove conflicts for {field_name}: "
            f"{conflicts}"
        )
    else:
        logger.debug(
            f"No conflicts detected for {field_name} "
            f"(add={len(add_values)}, remove={len(remove_values)})"
        )

    return conflicts


def validate_import_path_format(import_path: str) -> tuple[bool, str | None]:
    """Validate a Python import path format.

    Checks that the import path:
    - Has at least two dot-separated segments (module and class)
    - Each segment is a valid Python identifier
    - No segment is a Python reserved keyword
    - Contains no dangerous characters (security check)
    - Contains no path traversal sequences

    Args:
        import_path: The import path to validate (e.g., 'mypackage.module.MyClass').

    Returns:
        A tuple of (is_valid, error_message). If valid, error_message is None.
        If invalid, is_valid is False and error_message describes the problem.

    Example:
        >>> validate_import_path_format("mypackage.handlers.HttpClient")
        (True, None)
        >>> validate_import_path_format("singlemodule")
        (False, "Import path must include module and class (at least 2 segments)")
        >>> validate_import_path_format("my..module.Class")
        (False, "Import path cannot contain path separators or '..'")
        >>> validate_import_path_format("mypackage.class.Handler")
        (False, "Import path segment 'class' is a Python reserved keyword")
    """
    if not import_path or not import_path.strip():
        logger.debug("Import path validation failed: empty path")
        return False, "Import path cannot be empty"

    import_path = import_path.strip()

    # Security check: reject dangerous characters
    found_dangerous = [c for c in _DANGEROUS_IMPORT_CHARS if c in import_path]
    if found_dangerous:
        logger.debug(
            f"Import path validation failed: dangerous characters {found_dangerous}"
        )
        return False, f"Import path contains invalid characters: {found_dangerous}"

    # Security check: reject path traversal
    if ".." in import_path or "/" in import_path or "\\" in import_path:
        logger.debug("Import path validation failed: path traversal detected")
        return False, "Import path cannot contain path separators or '..'"

    # Split into segments and validate structure
    parts = import_path.split(".")
    if len(parts) < 2:
        logger.debug("Import path validation failed: fewer than 2 segments")
        return False, "Import path must include module and class (at least 2 segments)"

    # Check for empty segments
    if any(not part for part in parts):
        logger.debug("Import path validation failed: empty segment")
        return False, "Import path contains empty segment"

    # Validate each segment is a valid Python identifier
    for part in parts:
        if not is_valid_python_identifier(part):
            logger.debug(
                f"Import path validation failed: segment {part!r} is not a valid identifier"
            )
            return (
                False,
                f"Import path segment '{part}' is not a valid Python identifier",
            )

    # Check for Python reserved keywords (cannot be used as module/class names)
    for part in parts:
        if keyword.iskeyword(part):
            logger.debug(
                f"Import path validation failed: segment {part!r} is a reserved keyword"
            )
            return (
                False,
                f"Import path segment '{part}' is a Python reserved keyword",
            )

    logger.debug(f"Import path validation passed: {import_path!r}")
    return True, None


__all__ = [
    "is_valid_python_identifier",
    "is_valid_onex_name",
    "validate_import_path_format",
    "validate_string_list",
    "validate_onex_name_list",
    "detect_add_remove_conflicts",
]
