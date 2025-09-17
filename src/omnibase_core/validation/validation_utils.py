"""
Shared utilities for protocol validation across omni* ecosystem.
"""

import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


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
    violations: List[str] = None
    recommendations: List[str] = None

    def __post_init__(self):
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

    def __init__(self):
        self.methods = []
        self.imports = []
        self.class_name = ""

    def visit_ClassDef(self, node):
        """Extract class definition."""
        if "Protocol" in node.name and node.name[0].isupper():
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

    def visit_Import(self, node):
        """Extract imports."""
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
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

        # Create signature hash from methods
        methods_str = "|".join(sorted(extractor.methods))
        signature_hash = hashlib.md5(methods_str.encode()).hexdigest()[:12]

        return ProtocolInfo(
            name=extractor.class_name,
            file_path=str(file_path),
            repository=determine_repository_name(file_path),
            methods=extractor.methods,
            signature_hash=signature_hash,
            line_count=len(content.splitlines()),
            imports=extractor.imports,
        )

    except Exception as e:
        # Silently skip files that can't be parsed
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

    except Exception:
        return False


def find_protocol_files(directory: Path) -> List[Path]:
    """Find all files that likely contain protocols."""
    protocol_files = []

    if not directory.exists():
        return protocol_files

    for py_file in directory.rglob("*.py"):
        if is_protocol_file(py_file):
            protocol_files.append(py_file)

    return protocol_files


def extract_protocols_from_directory(directory: Path) -> List[ProtocolInfo]:
    """Extract all protocols from a directory."""
    protocols = []

    for protocol_file in find_protocol_files(directory):
        protocol_info = extract_protocol_signature(protocol_file)
        if protocol_info:
            protocols.append(protocol_info)

    return protocols
