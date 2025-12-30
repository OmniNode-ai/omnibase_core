from __future__ import annotations

"""
Shared utilities for protocol validation across omni* ecosystem.

This module provides common validation functions used throughout the ONEX framework:
- Python identifier validation
- ONEX naming convention validation
- Import path format validation
- Protocol signature extraction
- File and directory path validation
"""


import ast
import hashlib
import keyword
import logging
import re
from pathlib import Path

from omnibase_core.errors.exceptions import ExceptionInputValidationError
from omnibase_core.models.common.model_validation_result import ModelValidationResult
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
        return False
    return bool(_PYTHON_IDENTIFIER_PATTERN.match(name))


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
        return False
    if lowercase_only:
        return bool(_ONEX_LOWERCASE_NAME_PATTERN.match(name))
    return bool(_ONEX_NAME_PATTERN.match(name))


# =============================================================================
# Patch Validation Helper Functions
# =============================================================================


def validate_string_list(
    values: list[str] | None,
    field_name: str,
    *,
    min_length: int = 1,
    strip_whitespace: bool = True,
) -> list[str] | None:
    """Validate a list of strings, ensuring no empty values.

    This is a shared helper for patch validation that handles common
    string list validation patterns.

    Args:
        values: List of strings to validate, or None.
        field_name: Name of the field being validated (for error messages).
        min_length: Minimum length for each string after stripping.
        strip_whitespace: If True, strip whitespace from each value.

    Returns:
        Validated list of strings, or None if input was None.

    Raises:
        ValueError: If any string is empty or too short after processing.

    Example:
        >>> validate_string_list(["foo", "bar"], "events")
        ['foo', 'bar']
        >>> validate_string_list(["  foo  ", "bar"], "events")
        ['foo', 'bar']
        >>> validate_string_list(["", "bar"], "events")
        ValueError: events[0]: Value cannot be empty
    """
    if values is None:
        return None

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
) -> list[str] | None:
    """Validate a list of ONEX-compliant names.

    This is a shared helper for patch validation that validates names
    conform to ONEX naming conventions (alphanumeric + underscores).

    Args:
        values: List of names to validate, or None.
        field_name: Name of the field being validated (for error messages).
        normalize_lowercase: If True, normalize all names to lowercase.

    Returns:
        Validated and optionally normalized list of names, or None if input was None.

    Raises:
        ValueError: If any name is empty or contains invalid characters.

    Example:
        >>> validate_onex_name_list(["http_client", "kafka_producer"], "handlers")
        ['http_client', 'kafka_producer']
        >>> validate_onex_name_list(["HTTP_Client"], "handlers", normalize_lowercase=True)
        ['http_client']
        >>> validate_onex_name_list(["http-client"], "handlers")
        ValueError: handlers[0]: Name must contain only alphanumeric characters
        and underscores: 'http-client'
    """
    if values is None:
        return None

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
) -> list[str]:
    """Detect conflicts between add and remove operations.

    A conflict occurs when the same value appears in both the add and
    remove lists, which would result in undefined or contradictory behavior.

    Args:
        add_values: Values being added (may be pre-normalized).
        remove_values: Values being removed (may be pre-normalized).
        field_name: Name of the field (for logging).
        case_sensitive: If True, compare values case-sensitively.

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
    """
    if add_values is None or remove_values is None:
        return []

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
        return False, "Import path cannot be empty"

    import_path = import_path.strip()

    # Security check: reject dangerous characters
    found_dangerous = [c for c in _DANGEROUS_IMPORT_CHARS if c in import_path]
    if found_dangerous:
        return False, f"Import path contains invalid characters: {found_dangerous}"

    # Security check: reject path traversal
    if ".." in import_path or "/" in import_path or "\\" in import_path:
        return False, "Import path cannot contain path separators or '..'"

    # Split into segments and validate structure
    parts = import_path.split(".")
    if len(parts) < 2:
        return False, "Import path must include module and class (at least 2 segments)"

    # Check for empty segments
    if any(not part for part in parts):
        return False, "Import path contains empty segment"

    # Validate each segment is a valid Python identifier
    for part in parts:
        if not is_valid_python_identifier(part):
            return (
                False,
                f"Import path segment '{part}' is not a valid Python identifier",
            )

    # Check for Python reserved keywords (cannot be used as module/class names)
    for part in parts:
        if keyword.iskeyword(part):
            return (
                False,
                f"Import path segment '{part}' is a Python reserved keyword",
            )

    return True, None


def extract_protocol_signature(file_path: Path) -> ModelProtocolInfo | None:
    """Extract protocol signature from Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content)

        extractor = ModelProtocolSignatureExtractor()
        extractor.visit(tree)

        if not extractor.class_name or not extractor.methods:
            return None

        # Create signature hash from methods using SHA256 for security
        methods_str = "|".join(sorted(extractor.methods))
        signature_hash = hashlib.sha256(methods_str.encode()).hexdigest()

        return ModelProtocolInfo(
            name=extractor.class_name,
            file_path=str(file_path),
            repository=determine_repository_name(file_path),
            methods=extractor.methods,
            signature_hash=signature_hash,
            line_count=len(content.splitlines()),
            imports=extractor.imports,
        )

    except OSError as e:
        logger.exception(f"Error reading file {file_path}: {e}. Skipping file.")
        return None
    except UnicodeDecodeError as e:
        logger.exception(f"Encoding error in file {file_path}: {e}. Skipping file.")
        return None
    except SyntaxError as e:
        logger.warning(
            f"Skipping file with syntax error: {file_path}, "
            f"line {e.lineno}, offset {e.offset}: {e.msg}",
        )
        return None
    except Exception:  # fallback-ok: File processing errors should not stop the entire validation process
        # This is a safety net for truly unexpected errors.
        # logger.exception provides a full stack trace.
        logger.exception(f"Unexpected error processing {file_path}. Skipping file.")
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
    """Check if file likely contains protocols."""
    try:
        # Check filename
        if "protocol" in file_path.name.lower() or file_path.name.startswith(
            "protocol_",
        ):
            return True

        # Check file content (first 1000 chars for performance)
        content_sample = file_path.read_text(encoding="utf-8", errors="ignore")[:1000]
        return "class Protocol" in content_sample

    except OSError as e:
        logger.debug(f"Could not read file {file_path} for protocol check: {e}")
        return False
    except Exception as e:
        logger.debug(f"Unexpected error checking protocol file {file_path}: {e}")
        return False


def find_protocol_files(directory: Path) -> list[Path]:
    """Find all files that likely contain protocols."""
    protocol_files: list[Path] = []

    if not directory.exists():
        return protocol_files

    for py_file in directory.rglob("*.py"):
        if is_protocol_file(py_file):
            protocol_files.append(py_file)

    return protocol_files


def validate_directory_path(directory_path: Path, context: str = "directory") -> Path:
    """
    Validate that a directory path is safe and exists.

    Args:
        directory_path: Path to validate
        context: Context for error messages (e.g., 'repository', 'SPI directory')

    Returns:
        Resolved absolute path

    Raises:
        ExceptionInputValidation: If path is invalid
        PathTraversalError: If path attempts directory traversal
    """
    try:
        resolved_path = directory_path.resolve()
    except (OSError, ValueError) as e:
        msg = f"Invalid {context} path: {directory_path} ({e})"
        raise ExceptionInputValidationError(msg)

    # Check for potential directory traversal
    if ".." in str(directory_path):
        logger.warning(
            f"Potential directory traversal in {context} path: {directory_path}",
        )
        # Allow but log suspicious paths - some legitimate cases use ..

    if not resolved_path.exists():
        msg = f"{context.capitalize()} path does not exist: {resolved_path}"
        raise ExceptionInputValidationError(
            msg,
        )

    if not resolved_path.is_dir():
        msg = f"{context.capitalize()} path is not a directory: {resolved_path}"
        raise ExceptionInputValidationError(
            msg,
        )

    return resolved_path


def validate_file_path(file_path: Path, context: str = "file") -> Path:
    """
    Validate that a file path is safe and accessible.

    Args:
        file_path: Path to validate
        context: Context for error messages

    Returns:
        Resolved absolute path

    Raises:
        ExceptionInputValidation: If path is invalid
    """
    try:
        resolved_path = file_path.resolve()
    except (OSError, ValueError) as e:
        msg = f"Invalid {context} path: {file_path} ({e})"
        raise ExceptionInputValidationError(msg)

    if not resolved_path.exists():
        msg = f"{context.capitalize()} does not exist: {resolved_path}"
        raise ExceptionInputValidationError(
            msg,
        )

    if not resolved_path.is_file():
        msg = f"{context.capitalize()} is not a file: {resolved_path}"
        raise ExceptionInputValidationError(
            msg,
        )

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
    # Path validation
    "validate_directory_path",
    "validate_file_path",
]
