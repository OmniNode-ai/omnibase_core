"""
Shared utilities for protocol validation across omni* ecosystem.
"""

import ast
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from .exceptions import (
    FileProcessingError,
    InputValidationError,
    PathTraversalError,
    ProtocolParsingError,
)

# Configure logger for this module
logger = logging.getLogger(__name__)


@dataclass
class ProtocolInfo:
    """Information about a discovered protocol."""

    name: str
    file_path: str
    repository: str
    methods: List[str]
    signature_hash: str
    line_count: int
    imports: List[str]


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    success: bool
    message: str
    protocols_found: int = 0
    violations: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.violations is None:
            self.violations = []
        if self.recommendations is None:
            self.recommendations = []


@dataclass
class DuplicationInfo:
    """Information about protocol duplications."""

    signature_hash: str
    protocols: List[ProtocolInfo]
    duplication_type: str  # "exact", "name_conflict", "signature_match"
    recommendation: str


class ProtocolSignatureExtractor(ast.NodeVisitor):
    """Extracts protocol signature for comparison."""

    def __init__(self) -> None:
        self.methods = []
        self.imports = []
        self.class_name = ""

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class definition."""
        # Check if this class actually inherits from Protocol or typing.Protocol
        is_protocol = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Protocol":
                is_protocol = True
                break
            elif isinstance(base, ast.Attribute) and base.attr == "Protocol":
                is_protocol = True
                break

        if is_protocol:
            self.class_name = node.name
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Extract method signature
                    args = [arg.arg for arg in item.args.args if arg.arg != "self"]
                    returns = ast.unparse(item.returns) if item.returns else "None"
                    signature = f"{item.name}({', '.join(args)}) -> {returns}"
                    self.methods.append(signature)
                elif isinstance(item, ast.Expr) and isinstance(
                    item.value, ast.Constant
                ):
                    # Skip docstrings and ellipsis
                    continue
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Extract imports."""
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Extract from imports."""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")


def extract_protocol_signature(file_path: Path) -> Optional[ProtocolInfo]:
    """Extract protocol signature from Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
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

    except (IOError, OSError) as e:
        logger.error(f"Error reading file {file_path}: {e}. Skipping file.")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error in file {file_path}: {e}. Skipping file.")
        return None
    except SyntaxError as e:
        logger.warning(
            f"Skipping file with syntax error: {file_path}, "
            f"line {e.lineno}, offset {e.offset}: {e.msg}"
        )
        return None
    except Exception as e:
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
    elif any(
        word in name_lower
        for word in ["workflow", "task", "execution", "work", "queue"]
    ):
        return "workflow"

    # File operations
    elif any(
        word in name_lower for word in ["file", "reader", "writer", "storage", "stamp"]
    ):
        return "file_handling"

    # Event and messaging
    elif any(
        word in name_lower
        for word in ["event", "bus", "message", "pub", "communication"]
    ):
        return "event_bus"

    # Monitoring and observability
    elif any(
        word in name_lower
        for word in ["monitor", "metric", "observ", "trace", "health", "log"]
    ):
        return "monitoring"

    # Service integration
    elif any(
        word in name_lower
        for word in ["service", "client", "integration", "bridge", "registry"]
    ):
        return "integration"

    # Core ONEX architecture
    elif any(
        word in name_lower
        for word in ["reducer", "orchestrator", "compute", "effect", "onex"]
    ):
        return "core"

    # Testing and validation
    elif any(word in name_lower for word in ["test", "validation", "check", "verify"]):
        return "testing"

    # Data processing
    elif any(
        word in name_lower for word in ["data", "process", "transform", "serialize"]
    ):
        return "data"

    else:
        return "core"  # Default to core


def is_protocol_file(file_path: Path) -> bool:
    """Check if file likely contains protocols."""
    try:
        # Check filename
        if "protocol" in file_path.name.lower() or file_path.name.startswith(
            "protocol_"
        ):
            return True

        # Check file content (first 1000 chars for performance)
        content_sample = file_path.read_text(encoding="utf-8", errors="ignore")[:1000]
        return "class Protocol" in content_sample

    except (IOError, OSError) as e:
        logger.debug(f"Could not read file {file_path} for protocol check: {e}")
        return False
    except Exception as e:
        logger.debug(f"Unexpected error checking protocol file {file_path}: {e}")
        return False


def find_protocol_files(directory: Path) -> List[Path]:
    """Find all files that likely contain protocols."""
    protocol_files: List[Path] = []

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
        raise InputValidationError(f"Invalid {context} path: {directory_path} ({e})")

    # Check for potential directory traversal
    if ".." in str(directory_path):
        logger.warning(
            f"Potential directory traversal in {context} path: {directory_path}"
        )
        # Allow but log suspicious paths - some legitimate cases use ..

    if not resolved_path.exists():
        raise InputValidationError(
            f"{context.capitalize()} path does not exist: {resolved_path}"
        )

    if not resolved_path.is_dir():
        raise InputValidationError(
            f"{context.capitalize()} path is not a directory: {resolved_path}"
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
        raise InputValidationError(f"Invalid {context} path: {file_path} ({e})")

    if not resolved_path.exists():
        raise InputValidationError(
            f"{context.capitalize()} does not exist: {resolved_path}"
        )

    if not resolved_path.is_file():
        raise InputValidationError(
            f"{context.capitalize()} is not a file: {resolved_path}"
        )

    return resolved_path


def extract_protocols_from_directory(directory: Path) -> List[ProtocolInfo]:
    """Extract all protocols from a directory."""
    # Validate directory path first
    validated_directory = validate_directory_path(directory, "source directory")

    protocols = []
    protocol_files = find_protocol_files(validated_directory)

    logger.info(
        f"Found {len(protocol_files)} potential protocol files in {validated_directory}"
    )

    for protocol_file in protocol_files:
        protocol_info = extract_protocol_signature(protocol_file)
        if protocol_info:
            protocols.append(protocol_info)

    logger.info(
        f"Successfully extracted {len(protocols)} protocols from {validated_directory}"
    )
    return protocols
