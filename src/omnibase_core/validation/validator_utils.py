"""
Shared utilities for protocol validation across omni* ecosystem.

This module provides common validation functions used throughout the ONEX framework:
- Python identifier validation
- ONEX naming convention validation
- Import path format validation
- Protocol signature extraction
- File and directory path validation

Error Handling Patterns
-----------------------
This module uses two error handling patterns depending on the use case:

1. **Pydantic Validators** (validate_string_list, validate_onex_name_list):
   Raise ValueError because Pydantic @field_validator requires it.

2. **Standalone Validators** (validate_directory_path, validate_file_path):
   Raise ModelOnexError with proper EnumCoreErrorCode for structured error handling.

3. **Batch Processing** (extract_protocol_signature):
   Return None on errors to allow continued processing of remaining files.

Logging Conventions
-------------------
- DEBUG: Detailed trace information (validation results, successful operations)
- INFO: High-level operation summaries (number of files processed)
- WARNING: Recoverable issues that don't stop processing (skipped files)
- ERROR: Failures that will raise exceptions
"""

from __future__ import annotations

import ast
import hashlib
import keyword
import logging
import re
from pathlib import Path

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import ATTRIBUTE_ACCESS_ERRORS
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_duplication_info import ModelDuplicationInfo
from omnibase_core.models.validation.model_protocol_info import ModelProtocolInfo
from omnibase_core.models.validation.model_protocol_signature_extractor import (
    ModelProtocolSignatureExtractor,
)

# Configure logger for this module
logger = logging.getLogger(__name__)

# =============================================================================
# Pre-compiled Regex Patterns for Name Validation
# =============================================================================
# Thread-safe: ClassVar patterns are compiled once at module load time
# and re.Pattern objects are immutable, allowing safe concurrent access.

# Pattern for validating Python identifier format (starts with letter/underscore,
# followed by alphanumeric/underscore)
_PYTHON_IDENTIFIER_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Pattern for validating Python module path format (dot-separated identifiers)
_MODULE_PATH_PATTERN: re.Pattern[str] = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$"
)

# Pattern for validating ONEX naming convention (alphanumeric with underscores only)
_ONEX_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_]+$")

# Pattern for lowercase ONEX names (snake_case style)
_ONEX_LOWERCASE_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9_]+$")

# Characters that are dangerous in import paths (potential security issues)
_DANGEROUS_IMPORT_CHARS: frozenset[str] = frozenset(
    ["<", ">", "|", "&", ";", "`", "$", "'", '"', "*", "?", "[", "]"]
)


# =============================================================================
# Protocol Compliance Validation Functions
# =============================================================================


@allow_dict_any(reason="User-defined context kwargs for ModelOnexError")
def validate_protocol_compliance(
    obj: object,
    protocol: type,
    protocol_name: str,
    context: dict[str, object] | None = None,
) -> None:
    """Validate that an object implements required protocol methods.

    This function provides runtime validation for protocol compliance with
    detailed error messages when objects don't implement required protocols.
    It is designed for use after casting `object` types to protocols, providing
    better error messages than a bare `isinstance()` check.

    Args:
        obj: The object to validate.
        protocol: The Protocol class to check against. Must be decorated with
            `@runtime_checkable` to support isinstance() checks.
        protocol_name: Human-readable name for error messages (e.g., "ProtocolEventBus").
        context: Additional context for error reporting (e.g., {"service_name": "logger"}).

    Raises:
        ModelOnexError: If object doesn't implement the protocol, with error code
            TYPE_MISMATCH and detailed context including:
            - protocol: The protocol name
            - required_methods: List of methods the protocol requires
            - actual_type: The actual type name of the object

    Example:
        >>> from typing import Protocol, runtime_checkable
        >>> @runtime_checkable
        ... class ProtocolLogger(Protocol):
        ...     def log(self, message: str) -> None: ...
        ...
        >>> class GoodLogger:
        ...     def log(self, message: str) -> None:
        ...         print(message)
        ...
        >>> class BadLogger:
        ...     pass
        ...
        >>> validate_protocol_compliance(GoodLogger(), ProtocolLogger, "ProtocolLogger")
        >>> # No error raised
        >>> validate_protocol_compliance(BadLogger(), ProtocolLogger, "ProtocolLogger")
        ModelOnexError: Object does not implement ProtocolLogger

    Note:
        The protocol must be decorated with `@runtime_checkable` from the `typing`
        module. Without this decorator, `isinstance()` checks will raise a TypeError.
        All ONEX protocols should use `@runtime_checkable` when runtime checking
        is required.
    """
    if not isinstance(obj, protocol):
        # Get expected methods from protocol (exclude dunder methods and non-callables)
        required_methods = [
            m
            for m in dir(protocol)
            if not m.startswith("_") and callable(getattr(protocol, m, None))
        ]
        logger.debug(
            f"Protocol compliance validation failed: {type(obj).__name__} "
            f"does not implement {protocol_name}"
        )
        raise ModelOnexError(
            message=f"Object does not implement {protocol_name}",
            error_code=EnumCoreErrorCode.TYPE_MISMATCH,
            context={
                "protocol": protocol_name,
                "required_methods": required_methods,
                "actual_type": type(obj).__name__,
                **(context or {}),
            },
        )
    logger.debug(
        f"Protocol compliance validation passed: {type(obj).__name__} "
        f"implements {protocol_name}"
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


def extract_protocol_signature(file_path: Path) -> ModelProtocolInfo | None:
    """Extract protocol signature from Python file.

    Args:
        file_path: Path to the Python file to analyze.

    Returns:
        ModelProtocolInfo if a protocol class is found, None otherwise.

    Note:
        This function returns None rather than raising exceptions for file
        processing errors, as it's designed for batch processing where
        individual file failures should not stop the entire operation.

        Logging levels used:
        - DEBUG: Normal operations (no protocol found, successful extraction)
        - WARNING: Expected/recoverable errors (file access, encoding, syntax)
        - ERROR: Unexpected errors (logged via logger.exception)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content)

        extractor = ModelProtocolSignatureExtractor()
        extractor.visit(tree)

        if not extractor.class_name or not extractor.methods:
            logger.debug(f"No protocol class found in {file_path}")
            return None

        # Create signature hash from methods using SHA256 for security
        methods_str = "|".join(sorted(extractor.methods))
        signature_hash = hashlib.sha256(methods_str.encode()).hexdigest()

        protocol_info = ModelProtocolInfo(
            name=extractor.class_name,
            file_path=str(file_path),
            repository=determine_repository_name(file_path),
            methods=extractor.methods,
            signature_hash=signature_hash,
            line_count=len(content.splitlines()),
            imports=extractor.imports,
        )
        logger.debug(
            f"Extracted protocol {extractor.class_name!r} with "
            f"{len(extractor.methods)} methods from {file_path}"
        )
        return protocol_info

    except OSError as e:
        # Expected error: file access issues (permissions, not found, etc.)
        logger.warning(f"Skipping file due to read error: {file_path}: {e}")
        return None
    except UnicodeDecodeError as e:
        # Expected error: file encoding issues
        logger.warning(f"Skipping file due to encoding error: {file_path}: {e}")
        return None
    except SyntaxError as e:
        # Expected error: Python syntax errors in file
        logger.warning(
            f"Skipping file with syntax error: {file_path}, "
            f"line {e.lineno}, offset {e.offset}: {e.msg}",
        )
        return None
    except ValueError as e:
        # ast.parse raises ValueError for source containing null bytes
        logger.warning(f"Invalid source content in {file_path}: {e}. Skipping file.")
        return None
    except RecursionError:
        # Deeply nested AST structures can exceed recursion limit
        logger.warning(f"Recursion limit exceeded parsing {file_path}. Skipping file.")
        return None
    except MemoryError:
        # Extremely large files may exhaust memory during AST parsing
        logger.warning(f"Memory exhausted parsing {file_path}. Skipping file.")
        return None
    except ATTRIBUTE_ACCESS_ERRORS as e:
        # Handle AST processing errors: malformed tree structures, missing attributes,
        # or unexpected types from extractor operations
        logger.warning(f"Error processing AST in {file_path}: {e}. Skipping file.")
        return None


def determine_repository_name(file_path: Path) -> str:
    """Determine repository name from file path."""
    parts = Path(file_path).parts

    # Look for omni* directory names
    for part in parts:
        if part.startswith("omni"):
            return part

    # Fallback to directory structure analysis
    if "src" in parts:
        src_index = parts.index("src")
        if src_index > 0:
            return parts[src_index - 1]

    return "unknown"


def suggest_spi_location(protocol: ModelProtocolInfo) -> str:
    """Suggest appropriate SPI directory for a protocol."""
    name_lower = protocol.name.lower()

    # Agent-related protocols
    if any(
        word in name_lower
        for word in ["agent", "lifecycle", "coordinator", "pool", "manager"]
    ):
        return "agent"

    # Workflow and task management
    if any(
        word in name_lower
        for word in ["workflow", "task", "execution", "work", "queue"]
    ):
        return "workflow"

    # File operations
    if any(
        word in name_lower for word in ["file", "reader", "writer", "storage", "stamp"]
    ):
        return "file_handling"

    # Event and messaging
    if any(
        word in name_lower
        for word in ["event", "bus", "message", "pub", "communication"]
    ):
        return "event_bus"

    # Monitoring and observability
    if any(
        word in name_lower
        for word in ["monitor", "metric", "observ", "trace", "health", "log"]
    ):
        return "monitoring"

    # Service integration
    if any(
        word in name_lower
        for word in ["service", "client", "integration", "bridge", "registry"]
    ):
        return "integration"

    # Core ONEX architecture
    if any(
        word in name_lower
        for word in ["reducer", "orchestrator", "compute", "effect", "onex"]
    ):
        return "core"

    # Testing and validation
    if any(word in name_lower for word in ["test", "validation", "check", "verify"]):
        return "testing"

    # Data processing
    if any(
        word in name_lower for word in ["data", "process", "transform", "serialize"]
    ):
        return "data"

    return "core"  # Default to core


def is_protocol_file(file_path: Path) -> bool:
    """Check if file likely contains protocols.

    Args:
        file_path: Path to the Python file to check.

    Returns:
        True if file likely contains protocols, False otherwise.

    Note:
        This function returns False rather than raising exceptions for
        file access errors, as it's designed for file discovery where
        individual file failures should not stop the entire operation.

        Logging levels used:
        - DEBUG: Normal operations (filename check passed)
        - WARNING: Expected/recoverable errors (file access, encoding)
    """
    try:
        # Check filename
        if "protocol" in file_path.name.lower() or file_path.name.startswith(
            "protocol_",
        ):
            logger.debug(f"File {file_path} matches protocol filename pattern")
            return True

        # Check file content (first 1000 chars for performance)
        content_sample = file_path.read_text(encoding="utf-8", errors="ignore")[:1000]
        is_protocol = "class Protocol" in content_sample
        if is_protocol:
            logger.debug(f"File {file_path} contains protocol class definition")
        return is_protocol

    except (OSError, ValueError) as e:
        # Expected errors: file access issues (OSError), invalid path operations (ValueError)
        # UnicodeDecodeError not caught: read_text uses errors="ignore"
        logger.debug(f"Error checking protocol file {file_path}: {e}")
        return False
    except (AttributeError, TypeError) as e:
        # Handle path operation errors: missing attributes or unexpected types
        logger.debug(f"Path operation error checking protocol file {file_path}: {e}")
        return False


def find_protocol_files(directory: Path) -> list[Path]:
    """Find all files that likely contain protocols."""
    protocol_files: list[Path] = []

    if not directory.exists():
        logger.debug(f"Directory does not exist for protocol search: {directory}")
        return protocol_files

    for py_file in directory.rglob("*.py"):
        if is_protocol_file(py_file):
            protocol_files.append(py_file)

    logger.debug(f"Found {len(protocol_files)} protocol files in {directory}")
    return protocol_files


def validate_path_within_bounds(
    path: Path,
    allowed_root: Path | None = None,
    context: str = "path",
) -> Path:
    """
    Validate that a path stays within allowed boundaries (path traversal protection).

    This function prevents path traversal attacks by:
    1. Resolving the path to its canonical absolute form
    2. Checking the original input for traversal sequences (.., //, etc.)
    3. Optionally verifying the resolved path is under an allowed root

    Args:
        path: Path to validate
        allowed_root: Optional root directory the path must stay within.
            If provided, the resolved path must be equal to or a child of this root.
        context: Context for error messages

    Returns:
        Resolved absolute path

    Raises:
        ModelOnexError: If path contains traversal sequences or escapes allowed root

    Example:
        >>> validate_path_within_bounds(Path("../etc/passwd"), Path("/app"))
        ModelOnexError: Path traversal detected in path: ../etc/passwd
        >>> validate_path_within_bounds(Path("config/app.yaml"), Path("/app"))
        Path('/app/config/app.yaml')
    """
    path_str = str(path)

    # Security: Reject paths with traversal sequences
    # Check for various traversal patterns before resolution
    traversal_patterns = [
        "..",  # Parent directory traversal
        "//",  # Double slash (can bypass naive checks)
    ]

    for pattern in traversal_patterns:
        if pattern in path_str:
            msg = f"Path traversal detected in {context}: {path}"
            logger.error(msg)
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                context={
                    "path": path_str,
                    "context": context,
                    "pattern_detected": pattern,
                },
            )

    # Security: Reject absolute paths when relative expected (if root provided)
    if allowed_root is not None and path.is_absolute():
        msg = f"Absolute path not allowed for {context}: {path}"
        logger.error(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
            context={
                "path": path_str,
                "context": context,
                "reason": "absolute_path_rejected",
            },
        )

    try:
        resolved_path = path.resolve()
    except (OSError, ValueError) as e:
        msg = f"Invalid {context} path: {path} ({e})"
        logger.exception(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            context={
                "path": path_str,
                "context": context,
                "error": str(e),
            },
        ) from e

    # Security: Verify path is within allowed root (bounds checking)
    if allowed_root is not None:
        try:
            resolved_root = allowed_root.resolve()
            # Check if resolved_path is the same as or a child of resolved_root
            # Use is_relative_to for Python 3.9+ compatibility
            if not resolved_path.is_relative_to(resolved_root):
                msg = f"Path escapes allowed directory for {context}: {path}"
                logger.error(msg)
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                    context={
                        "path": path_str,
                        "resolved_path": str(resolved_path),
                        "allowed_root": str(resolved_root),
                        "context": context,
                    },
                )
        except (OSError, ValueError) as e:
            msg = f"Invalid allowed_root path: {allowed_root} ({e})"
            logger.exception(msg)
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                context={
                    "allowed_root": str(allowed_root),
                    "context": context,
                    "error": str(e),
                },
            ) from e

    logger.debug(f"Validated {context} path within bounds: {resolved_path}")
    return resolved_path


def validate_directory_path(
    directory_path: Path,
    context: str = "directory",
    *,
    allowed_root: Path | None = None,
) -> Path:
    """
    Validate that a directory path is safe and exists.

    Security: This function now rejects path traversal attempts rather than
    just logging a warning. Use the allowed_root parameter for strict bounds
    checking when validating user-provided paths.

    Args:
        directory_path: Path to validate
        context: Context for error messages (e.g., 'repository', 'SPI directory')
        allowed_root: Optional root directory the path must stay within.
            If provided, the resolved path must be equal to or a child of this root.

    Returns:
        Resolved absolute path

    Raises:
        ModelOnexError: If path is invalid, contains traversal sequences,
            does not exist, or is not a directory
    """
    # Security: Check for path traversal before any other validation
    path_str = str(directory_path)
    if ".." in path_str:
        msg = f"Path traversal detected in {context} path: {directory_path}"
        logger.error(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
            context={
                "path": path_str,
                "context": context,
                "pattern_detected": "..",
            },
        )

    try:
        resolved_path = directory_path.resolve()
    except (OSError, ValueError) as e:
        msg = f"Invalid {context} path: {directory_path} ({e})"
        logger.exception(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            path=str(directory_path),
            context=context,
        ) from e

    # Security: Verify path is within allowed root (bounds checking)
    if allowed_root is not None:
        try:
            resolved_root = allowed_root.resolve()
            if not resolved_path.is_relative_to(resolved_root):
                msg = f"Path escapes allowed directory for {context}: {directory_path}"
                logger.error(msg)
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                    context={
                        "path": path_str,
                        "resolved_path": str(resolved_path),
                        "allowed_root": str(resolved_root),
                        "context": context,
                    },
                )
        except (OSError, ValueError) as e:
            msg = f"Invalid allowed_root path: {allowed_root} ({e})"
            logger.exception(msg)
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                context={
                    "allowed_root": str(allowed_root),
                    "context": context,
                    "error": str(e),
                },
            ) from e

    if not resolved_path.exists():
        msg = f"{context.capitalize()} path does not exist: {resolved_path}"
        logger.error(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.DIRECTORY_NOT_FOUND,
            path=str(resolved_path),
            context=context,
        )

    if not resolved_path.is_dir():
        msg = f"{context.capitalize()} path is not a directory: {resolved_path}"
        logger.error(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            path=str(resolved_path),
            context=context,
        )

    logger.debug(f"Validated {context} path: {resolved_path}")
    return resolved_path


def validate_file_path(
    file_path: Path,
    context: str = "file",
    *,
    allowed_root: Path | None = None,
) -> Path:
    """
    Validate that a file path is safe and accessible.

    Security: This function now checks for path traversal attempts and optionally
    validates that the path stays within an allowed root directory.

    Args:
        file_path: Path to validate
        context: Context for error messages
        allowed_root: Optional root directory the path must stay within.
            If provided, the resolved path must be equal to or a child of this root.

    Returns:
        Resolved absolute path

    Raises:
        ModelOnexError: If path is invalid, contains traversal sequences,
            does not exist, or is not a file
    """
    # Security: Check for path traversal before any other validation
    path_str = str(file_path)
    if ".." in path_str:
        msg = f"Path traversal detected in {context} path: {file_path}"
        logger.error(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
            context={
                "path": path_str,
                "context": context,
                "pattern_detected": "..",
            },
        )

    try:
        resolved_path = file_path.resolve()
    except (OSError, ValueError) as e:
        msg = f"Invalid {context} path: {file_path} ({e})"
        logger.exception(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            path=str(file_path),
            context=context,
        ) from e

    # Security: Verify path is within allowed root (bounds checking)
    if allowed_root is not None:
        try:
            resolved_root = allowed_root.resolve()
            if not resolved_path.is_relative_to(resolved_root):
                msg = f"Path escapes allowed directory for {context}: {file_path}"
                logger.error(msg)
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
                    context={
                        "path": path_str,
                        "resolved_path": str(resolved_path),
                        "allowed_root": str(resolved_root),
                        "context": context,
                    },
                )
        except (OSError, ValueError) as e:
            msg = f"Invalid allowed_root path: {allowed_root} ({e})"
            logger.exception(msg)
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                context={
                    "allowed_root": str(allowed_root),
                    "context": context,
                    "error": str(e),
                },
            ) from e

    if not resolved_path.exists():
        msg = f"{context.capitalize()} does not exist: {resolved_path}"
        logger.error(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            path=str(resolved_path),
            context=context,
        )

    if not resolved_path.is_file():
        msg = f"{context.capitalize()} is not a file: {resolved_path}"
        logger.error(msg)
        raise ModelOnexError(
            message=msg,
            error_code=EnumCoreErrorCode.INVALID_INPUT,
            path=str(resolved_path),
            context=context,
        )

    logger.debug(f"Validated {context} path: {resolved_path}")
    return resolved_path


def extract_protocols_from_directory(directory: Path) -> list[ModelProtocolInfo]:
    """Extract all protocols from a directory."""
    # Validate directory path first
    validated_directory = validate_directory_path(directory, "source directory")

    protocols = []
    protocol_files = find_protocol_files(validated_directory)

    logger.info(
        f"Found {len(protocol_files)} potential protocol files in "
        f"{validated_directory}",
    )

    for protocol_file in protocol_files:
        protocol_info = extract_protocol_signature(protocol_file)
        if protocol_info:
            protocols.append(protocol_info)

    logger.info(
        f"Successfully extracted {len(protocols)} protocols from {validated_directory}",
    )
    return protocols


# Export all public functions, classes, and types
__all__ = [
    # Models re-exported for convenience
    "ModelDuplicationInfo",
    "ModelProtocolInfo",
    "ModelValidationResult",
    # Protocol compliance validation
    "validate_protocol_compliance",
    # Name and identifier validation
    "is_valid_python_identifier",
    "is_valid_onex_name",
    "validate_import_path_format",
    # Patch validation helpers
    "validate_string_list",
    "validate_onex_name_list",
    "detect_add_remove_conflicts",
    # Protocol extraction
    "determine_repository_name",
    "extract_protocol_signature",
    "extract_protocols_from_directory",
    "find_protocol_files",
    "is_protocol_file",
    "suggest_spi_location",
    # Path validation (with security)
    "validate_directory_path",
    "validate_file_path",
    "validate_path_within_bounds",
]
