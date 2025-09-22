"""
Shared utilities for protocol validation across omni* ecosystem.
"""

from __future__ import annotations

import ast
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict


class ValidationMetadataType(TypedDict, total=False):
    """Type-safe validation metadata structure."""

    protocols_found: int
    recommendations: list[str]
    signature_hashes: list[str]
    file_count: int
    duplication_count: int
    suggestions: list[str]
    total_unions: int
    violations_found: int
    message: str
    validation_type: str
    yaml_files_found: int
    manual_yaml_violations: int
    max_violations: int
    files_with_violations: list[str]
    strict_mode: bool
    error: str
    max_unions: int
    complex_patterns: int


from .exceptions import (
    InputValidationError,
)
from .model_protocol_info import ProtocolInfo
from .model_protocol_signature_extractor import ProtocolSignatureExtractor

# Configure logger for this module
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    success: bool
    errors: list[str]
    files_checked: int = 0
    violations_found: int = 0
    files_with_violations: int = 0
    metadata: ValidationMetadataType | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}

    # Legacy compatibility properties
    @property
    def message(self) -> str:
        """Legacy message property for backward compatibility."""
        if self.success:
            return f"Validation passed: {self.files_checked} files checked"
        return f"Validation failed: {len(self.errors)} errors found"

    @property
    def violations(self) -> list[str]:
        """Legacy violations property for backward compatibility."""
        return self.errors

    @property
    def protocols_found(self) -> int:
        """Legacy protocols_found property for backward compatibility."""
        if not self.metadata:
            return 0
        value = self.metadata.get("protocols_found", 0)
        return int(value) if isinstance(value, (int, float)) else 0

    @property
    def recommendations(self) -> list[str]:
        """Legacy recommendations property for backward compatibility."""
        if not self.metadata:
            return []
        value = self.metadata.get("recommendations", [])
        return list(value) if isinstance(value, list) else []


@dataclass
class DuplicationInfo:
    """Information about protocol duplications."""

    signature_hash: str
    protocols: list[ProtocolInfo]
    duplication_type: str  # "exact", "name_conflict", "signature_match"
    recommendation: str


def extract_protocol_signature(file_path: Path) -> ProtocolInfo | None:
    """Extract protocol signature from Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            tree = ast.parse(content)

        extractor = ProtocolSignatureExtractor()
        extractor.visit(tree)

        if not extractor.class_name or not extractor.methods:
            return None

        # Create signature hash from methods using SHA256 for security
        methods_str = "|".join(sorted(extractor.methods))
        signature_hash = hashlib.sha256(methods_str.encode()).hexdigest()

        return ProtocolInfo(
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
    except Exception:
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


def suggest_spi_location(protocol: ProtocolInfo) -> str:
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
        InputValidationError: If path is invalid
        PathTraversalError: If path attempts directory traversal
    """
    try:
        resolved_path = directory_path.resolve()
    except (OSError, ValueError) as e:
        msg = f"Invalid {context} path: {directory_path} ({e})"
        raise InputValidationError(msg)

    # Check for potential directory traversal
    if ".." in str(directory_path):
        logger.warning(
            f"Potential directory traversal in {context} path: {directory_path}",
        )
        # Allow but log suspicious paths - some legitimate cases use ..

    if not resolved_path.exists():
        msg = f"{context.capitalize()} path does not exist: {resolved_path}"
        raise InputValidationError(
            msg,
        )

    if not resolved_path.is_dir():
        msg = f"{context.capitalize()} path is not a directory: {resolved_path}"
        raise InputValidationError(
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
        InputValidationError: If path is invalid
    """
    try:
        resolved_path = file_path.resolve()
    except (OSError, ValueError) as e:
        msg = f"Invalid {context} path: {file_path} ({e})"
        raise InputValidationError(msg)

    if not resolved_path.exists():
        msg = f"{context.capitalize()} does not exist: {resolved_path}"
        raise InputValidationError(
            msg,
        )

    if not resolved_path.is_file():
        msg = f"{context.capitalize()} is not a file: {resolved_path}"
        raise InputValidationError(
            msg,
        )

    return resolved_path


def extract_protocols_from_directory(directory: Path) -> list[ProtocolInfo]:
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
