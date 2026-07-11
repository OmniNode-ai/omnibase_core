# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Shared utilities for protocol validation across omni* ecosystem.

Common validation functions used throughout the ONEX framework:
- Python identifier validation
- ONEX naming convention validation
- Import path format validation
- Protocol signature extraction
- File and directory path validation

The pure name/identifier and patch-list validators (``is_valid_onex_name``,
``is_valid_python_identifier``, ``validate_import_path_format``,
``validate_string_list``, ``validate_onex_name_list``,
``detect_add_remove_conflicts``) were relocated to
:mod:`omnibase_core.utils.util_name_validation` under OMN-14331 (epic OMN-3210)
so that domain MODELS can reuse them without importing the ``validation`` layer.
They are re-exported here to preserve this module's public surface.

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
import logging
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

# Pure name/identifier and patch-list validators (relocated below `models` under
# OMN-14331). Re-exported so `omnibase_core.validation.validator_utils` keeps its
# historical public API for services, tests, and the validation package __init__.
from omnibase_core.utils.util_name_validation import (
    detect_add_remove_conflicts,
    is_valid_onex_name,
    is_valid_python_identifier,
    validate_import_path_format,
    validate_onex_name_list,
    validate_string_list,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


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

    Runtime validation for protocol compliance with
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
    # Name and identifier validation (relocated to utils.util_name_validation,
    # re-exported here for backwards compatibility)
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
]
