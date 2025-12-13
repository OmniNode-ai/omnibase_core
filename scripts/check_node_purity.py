#!/usr/bin/env python3
"""
ONEX Node Purity Validation.

AST-based purity checks to ensure declarative nodes (COMPUTE, REDUCER) remain pure
and do not contain I/O operations, network calls, or other side effects.

This protects the ONEX architecture from contributors adding "convenience shortcuts"
that would violate the purity guarantees of declarative nodes.

PURITY GUARANTEES:
- COMPUTE nodes: Pure transformations only (no I/O, no side effects)
- REDUCER nodes: Pure state management via FSM (no I/O in reduction logic)
- EFFECT nodes: Explicitly allowed to have side effects (not checked)
- ORCHESTRATOR nodes: Coordination logic only (workflow definitions)

FORBIDDEN PATTERNS IN PURE NODES:
1. Networking libraries: requests, httpx, aiohttp, socket, urllib, urllib3
2. Filesystem operations: open(), pathlib write operations, os.write, os.read
3. Subprocess calls: subprocess, os.system, os.popen, os.spawn*
4. Threading: threading, multiprocessing, concurrent.futures (except in base class)
5. Module-level `import logging` (use structured logging via container)
6. Class-level mutable data (lists, dicts, sets as class attributes)
7. Caching decorators: @lru_cache, @cache, @cached_property (state leakage)
8. External library imports outside core or SPI allowlist

ALLOWED PATTERNS:
- Standard library pure modules (typing, dataclasses, enum, abc, etc.)
- Pydantic models and validation
- omnibase_core.* imports (core framework)
- omnibase_spi.* imports (SPI layer - when applicable)
- Time measurement (time.perf_counter for metrics)
- Hashlib for deterministic hashing
- Container-based dependency injection

Usage:
    poetry run python scripts/check_node_purity.py
    poetry run python scripts/check_node_purity.py --verbose
    poetry run python scripts/check_node_purity.py --strict
    poetry run python scripts/check_node_purity.py --file src/omnibase_core/nodes/node_compute.py

Exit Codes:
    0 - All nodes pass purity checks
    1 - Purity violations detected (blocks PR)
    2 - Script error (invalid arguments, file not found, etc.)
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import NamedTuple


class ViolationType(Enum):
    """Types of purity violations."""

    NETWORKING_IMPORT = "networking_import"
    FILESYSTEM_OPERATION = "filesystem_operation"
    SUBPROCESS_IMPORT = "subprocess_import"
    THREADING_IMPORT = "threading_import"
    LOGGING_IMPORT = "logging_import"
    CLASS_MUTABLE_DATA = "class_mutable_data"
    CACHING_DECORATOR = "caching_decorator"
    FORBIDDEN_IMPORT = "forbidden_import"
    INVALID_INHERITANCE = "invalid_inheritance"
    OPEN_CALL = "open_call"
    PATHLIB_WRITE = "pathlib_write"
    # New violation types for OMN-203: Declarative node purity linter
    ANY_IMPORT = "any_import"
    ANY_TYPE_HINT = "any_type_hint"
    DICT_ANY_TYPE_HINT = "dict_any_type_hint"
    LEGACY_MIXIN_IMPORT = "legacy_mixin_import"
    EVENT_BUS_IMPORT = "event_bus_import"


class Severity(Enum):
    """Severity levels for violations."""

    ERROR = "error"  # Blocks CI
    WARNING = "warning"  # Informational (strict mode only)


@dataclass
class PurityViolation:
    """A single purity violation found in a node file."""

    file_path: Path
    line_number: int
    column: int
    violation_type: ViolationType
    severity: Severity
    message: str
    suggestion: str
    code_snippet: str = ""

    def format(self, verbose: bool = False) -> str:
        """Format violation for output."""
        location = f"{self.file_path}:{self.line_number}:{self.column}"
        level = "ERROR" if self.severity == Severity.ERROR else "WARNING"

        result = f"[{level}] {location}\n"
        result += f"  {self.violation_type.value}: {self.message}\n"
        result += f"  Suggestion: {self.suggestion}\n"

        if verbose and self.code_snippet:
            result += f"  Code: {self.code_snippet}\n"

        return result


class PurityCheckResult(NamedTuple):
    """Result of purity check for a single file."""

    file_path: Path
    node_class_name: str | None
    node_type: str | None  # "compute", "reducer", "effect", "orchestrator"
    violations: list[PurityViolation]
    is_pure: bool
    skip_reason: str | None


# ==============================================================================
# FORBIDDEN PATTERNS CONFIGURATION
# ==============================================================================

# Networking libraries - FORBIDDEN in pure nodes
FORBIDDEN_NETWORKING_MODULES = frozenset(
    {
        "requests",
        "httpx",
        "aiohttp",
        "urllib",
        "urllib3",
        "socket",
        "http",
        "http.client",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "nntplib",
        "telnetlib",
        "ssl",
        "websocket",
        "websockets",
        "tornado",
        "grpc",
        "zeromq",
        "pyzmq",
        "kafka",
        "redis",
        "pymongo",
        "psycopg2",
        "asyncpg",
        "aiomysql",
        "sqlalchemy",  # Contains I/O operations
        "boto3",
        "azure",
        "google.cloud",
    }
)

# Subprocess/OS execution - FORBIDDEN in pure nodes
FORBIDDEN_SUBPROCESS_MODULES = frozenset(
    {
        "subprocess",
        "os.system",
        "os.popen",
        "os.spawn",
        "os.spawnl",
        "os.spawnle",
        "os.spawnlp",
        "os.spawnlpe",
        "os.spawnv",
        "os.spawnve",
        "os.spawnvp",
        "os.spawnvpe",
        "os.exec",
        "os.execl",
        "os.execle",
        "os.execlp",
        "os.execlpe",
        "os.execv",
        "os.execve",
        "os.execvp",
        "os.execvpe",
        "pty",
        "pexpect",
        "sh",
        "plumbum",
    }
)

# Threading/multiprocessing - FORBIDDEN in pure nodes (except base class utilities)
FORBIDDEN_THREADING_MODULES = frozenset(
    {
        "threading",
        "multiprocessing",
        "concurrent.futures",
        "asyncio.subprocess",
    }
)

# Filesystem write operations - functions that modify filesystem
# NOTE: open() is handled specially in visit_Call to allow read-only mode
FORBIDDEN_FILESYSTEM_FUNCTIONS = frozenset(
    {
        # "open" is NOT listed here - it's handled specially in visit_Call
        # to allow read-only mode (e.g., open(..., 'r'))
        "os.write",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "os.removedirs",
        "os.rename",
        "os.renames",
        "os.replace",
        "os.mkdir",
        "os.makedirs",
        "os.symlink",
        "os.link",
        "os.truncate",
        "shutil.copy",
        "shutil.copy2",
        "shutil.copytree",
        "shutil.move",
        "shutil.rmtree",
        "shutil.chown",
    }
)

# Pathlib write methods
FORBIDDEN_PATHLIB_METHODS = frozenset(
    {
        "write_text",
        "write_bytes",
        "unlink",
        "rmdir",
        "mkdir",
        "rename",
        "replace",
        "symlink_to",
        "hardlink_to",
        "touch",
        "chmod",
        "lchmod",
    }
)

# Caching decorators that introduce state
FORBIDDEN_CACHING_DECORATORS = frozenset(
    {
        "lru_cache",
        "cache",
        "cached_property",
        "functools.lru_cache",
        "functools.cache",
        "functools.cached_property",
    }
)

# ==============================================================================
# DECLARATIVE NODE PURITY CONFIGURATION (OMN-203)
# ==============================================================================

# Legacy mixins - FORBIDDEN in declarative nodes (NodeCompute, NodeReducer)
FORBIDDEN_LEGACY_MIXINS = frozenset(
    {
        "MixinEventBus",
        "MixinEventDrivenNode",
        "MixinEventHandler",
        "MixinEventListener",
        "MixinServiceRegistry",
    }
)

# Event bus module prefixes - FORBIDDEN in declarative nodes
FORBIDDEN_EVENT_BUS_MODULES = frozenset(
    {
        "omnibase_core.events",
        "omnibase_core.models.event_bus",
        "omnibase_core.models.events",
    }
)

# Event bus component names - FORBIDDEN in declarative nodes
FORBIDDEN_EVENT_BUS_NAMES = frozenset(
    {
        "ProtocolEventBus",
        "ModelEventEnvelope",
        "ModelEventBusConfig",
        "ModelEventBusInputState",
        "ModelEventBusOutputState",
        "ModelEventConfig",
        "ModelEventPublishIntent",
    }
)

# Decorators that allow Dict[str, Any] exemption
ALLOW_DICT_ANY_DECORATORS = frozenset(
    {
        "allow_dict_any",
        "allow_dict_str_any",
    }
)

# ALLOWED standard library modules (pure operations only)
ALLOWED_STDLIB_MODULES = frozenset(
    {
        # Core language
        "typing",
        "typing_extensions",
        "types",
        "abc",
        "asyncio",  # Async/await is allowed (no direct I/O)
        "collections",
        "collections.abc",
        "dataclasses",
        "enum",
        "functools",  # But NOT caching decorators
        "itertools",
        "operator",
        "copy",
        "re",
        "string",
        "textwrap",
        "difflib",
        "unicodedata",
        # Numbers and math
        "decimal",
        "fractions",
        "numbers",
        "math",
        "cmath",
        "statistics",
        "random",  # Pseudo-random is acceptable for pure computation
        # Data structures
        "array",
        "struct",
        "codecs",
        "json",
        "base64",
        "binascii",
        "quopri",
        "uu",
        # Date/time (reading only)
        "datetime",
        "calendar",
        "time",  # For perf_counter (metrics)
        "zoneinfo",
        # Crypto (pure hashing)
        "hashlib",
        "hmac",
        "secrets",
        # UUID generation
        "uuid",
        # Path parsing (not writing)
        "pathlib",
        "os.path",
        "posixpath",
        "ntpath",
        # Inspection
        "inspect",
        "dis",
        "ast",
        "traceback",
        "warnings",
        "contextlib",
        # Python internals
        "__future__",
        "builtins",
        "sys",  # For type checking only
    }
)

# ALLOWED framework modules
ALLOWED_FRAMEWORK_PREFIXES = (
    "omnibase_core.",
    "omnibase_spi.",
    "pydantic",
    "pydantic_settings",
)

# Valid base classes for nodes
VALID_NODE_BASE_CLASSES = frozenset(
    {
        "NodeCoreBase",
        "Generic",
        "ABC",
        # Mixins are allowed
        "MixinFSMExecution",
        "MixinWorkflowExecution",
        "MixinDiscoveryResponder",
        "MixinEventHandler",
        "MixinEventListener",
        "MixinNodeExecutor",
        "MixinNodeLifecycle",
        "MixinRequestResponseIntrospection",
        "MixinWorkflowSupport",
        "MixinContractMetadata",
    }
)


# ==============================================================================
# AST VISITORS
# ==============================================================================


class NodeTypeFinder(ast.NodeVisitor):
    """First pass AST visitor to find node classes and determine purity requirements.

    This visitor scans the AST to identify ONEX node classes and determine
    whether they should be subject to purity checks. COMPUTE and REDUCER
    nodes require purity; EFFECT and ORCHESTRATOR nodes do not.

    Attributes:
        node_class_name: Name of the node class found, if any.
        node_type: Type of node ('compute', 'reducer', 'effect', 'orchestrator').
        is_pure_node: True if this is a COMPUTE or REDUCER node requiring purity.
    """

    def __init__(self) -> None:
        """Initialize the NodeTypeFinder with default values."""
        self.node_class_name: str | None = None
        self.node_type: str | None = None
        self.is_pure_node: bool = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Find node class definitions and determine their type.

        Args:
            node: AST class definition node to analyze.
        """
        if self._is_node_class(node):
            self.node_class_name = node.name
            self.node_type = self._determine_node_type(node)
            self.is_pure_node = self.node_type in ("compute", "reducer")
        self.generic_visit(node)

    def _is_node_class(self, node: ast.ClassDef) -> bool:
        """Check if class is an ONEX Node class (first pass).

        Used during the initial AST traversal to identify node classes
        for purity requirement determination.

        Args:
            node: AST class definition node to check.

        Returns:
            True if class inherits from a Node base class.
        """
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name in (
                "NodeCoreBase",
                "NodeCompute",
                "NodeEffect",
                "NodeReducer",
                "NodeOrchestrator",
            ):
                return True
            if base_name and base_name.startswith("Node"):
                return True
        return False

    def _determine_node_type(self, node: ast.ClassDef) -> str | None:
        """Determine the type of node from class name or base classes (first pass).

        Used during initial AST traversal to classify node type for
        purity requirement determination.

        Args:
            node: AST class definition node to analyze.

        Returns:
            Node type string ('compute', 'effect', 'reducer', 'orchestrator')
            or None if type cannot be determined.
        """
        class_name = node.name.lower()

        if "compute" in class_name:
            return "compute"
        if "effect" in class_name:
            return "effect"
        if "reducer" in class_name:
            return "reducer"
        if "orchestrator" in class_name:
            return "orchestrator"

        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name:
                base_lower = base_name.lower()
                if "compute" in base_lower:
                    return "compute"
                if "effect" in base_lower:
                    return "effect"
                if "reducer" in base_lower:
                    return "reducer"
                if "orchestrator" in base_lower:
                    return "orchestrator"

        return None

    def _get_base_name(self, base: ast.expr) -> str | None:
        """Extract base class name from AST expression (first pass helper).

        Args:
            base: AST expression representing a base class.

        Returns:
            String name of the base class, or None if cannot be extracted.
        """
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        if isinstance(base, ast.Subscript):
            if isinstance(base.value, ast.Name):
                return base.value.id
        return None


@dataclass
class PurityAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze node purity violations (second pass).

    Scans the AST for patterns that violate purity guarantees in
    COMPUTE and REDUCER nodes, including forbidden imports, I/O operations,
    mutable class data, and caching decorators.

    Attributes:
        file_path: Path to the file being analyzed.
        source_lines: List of source code lines for snippet extraction.
        violations: List of detected purity violations.
        node_type: Type of the node being analyzed.
        node_class_name: Name of the node class being analyzed.
        is_pure_node: Whether this node requires purity checking.
        current_class: Name of the class currently being visited.
        in_type_checking_block: Whether currently inside TYPE_CHECKING block.
        excluded_lines: Set of line numbers with ONEX_EXCLUDE comments.
        class_allow_dict_any: Whether current class has @allow_dict_any.
        function_allow_dict_any_lines: Set of line numbers for functions with @allow_dict_any.
    """

    file_path: Path
    source_lines: list[str]
    violations: list[PurityViolation] = field(default_factory=list)
    node_type: str | None = None
    node_class_name: str | None = None
    is_pure_node: bool = False
    current_class: str | None = None
    in_type_checking_block: bool = False
    excluded_lines: set[int] = field(default_factory=set)
    class_allow_dict_any: bool = False
    function_allow_dict_any_lines: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Parse source lines for ONEX_EXCLUDE comments after initialization."""
        self._parse_onex_exclude_comments()

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements for forbidden modules.

        Args:
            node: AST import node to check.
        """
        if not self.is_pure_node:
            self.generic_visit(node)
            return

        # Skip imports inside TYPE_CHECKING blocks
        if self.in_type_checking_block:
            self.generic_visit(node)
            return

        # Skip imports with ONEX_EXCLUDE comments
        line_num = getattr(node, "lineno", 0)
        if self._is_line_excluded(line_num):
            self.generic_visit(node)
            return

        for alias in node.names:
            module_name = alias.name
            self._check_module_import(node, module_name)

            # Check for event bus module imports (OMN-203)
            self._check_event_bus_module_import(node, module_name)

            # Check for legacy mixin module imports (OMN-203)
            # e.g., import omnibase_core.mixins.mixin_event_bus
            self._check_legacy_mixin_module_import(node, module_name)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check 'from ... import ...' statements for forbidden modules.

        Args:
            node: AST import-from node to check.
        """
        if not self.is_pure_node:
            self.generic_visit(node)
            return

        # Skip imports inside TYPE_CHECKING blocks
        if self.in_type_checking_block:
            self.generic_visit(node)
            return

        # Skip imports with ONEX_EXCLUDE comments
        line_num = getattr(node, "lineno", 0)
        if self._is_line_excluded(line_num):
            self.generic_visit(node)
            return

        module_name = node.module or ""

        # Check the module itself
        self._check_module_import(node, module_name)

        # Check for event bus module imports (OMN-203)
        self._check_event_bus_module_import(node, module_name)

        # Check specific imports
        for alias in node.names:
            imported_name = alias.name
            full_name = (
                f"{module_name}.{imported_name}" if module_name else imported_name
            )

            # Check for typing.Any import (OMN-203)
            if module_name == "typing" and imported_name == "Any":
                self._add_violation(
                    node,
                    ViolationType.ANY_IMPORT,
                    Severity.ERROR,
                    "Importing 'Any' from typing is forbidden in declarative nodes",
                    "Use specific types, TypedDict, or Pydantic models instead",
                )

            # Check for caching decorators
            if (
                imported_name in FORBIDDEN_CACHING_DECORATORS
                or full_name in FORBIDDEN_CACHING_DECORATORS
            ):
                self._add_violation(
                    node,
                    ViolationType.CACHING_DECORATOR,
                    Severity.ERROR,
                    f"Caching decorator '{imported_name}' introduces mutable state",
                    "Use container-provided caching services or ModelComputeCache",
                )

            # Check for legacy mixin imports (OMN-203)
            if imported_name in FORBIDDEN_LEGACY_MIXINS:
                self._add_violation(
                    node,
                    ViolationType.LEGACY_MIXIN_IMPORT,
                    Severity.ERROR,
                    f"Legacy mixin '{imported_name}' is forbidden in declarative nodes",
                    "Remove mixin or use Effect nodes for event-driven functionality",
                )

            # Check for event bus component imports (OMN-203)
            if imported_name in FORBIDDEN_EVENT_BUS_NAMES:
                self._add_violation(
                    node,
                    ViolationType.EVENT_BUS_IMPORT,
                    Severity.ERROR,
                    f"Event bus component '{imported_name}' is forbidden in declarative nodes",
                    "Use Effect nodes for event bus operations or emit intents instead",
                )

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Track TYPE_CHECKING blocks to skip import checks inside them.

        Args:
            node: AST if statement node to check.
        """
        # Check if this is a TYPE_CHECKING block
        if self._is_type_checking_block(node):
            prev_in_type_checking = self.in_type_checking_block
            self.in_type_checking_block = True
            self.generic_visit(node)
            self.in_type_checking_block = prev_in_type_checking
        else:
            self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Analyze class definitions for purity violations.

        Checks inheritance, class-level mutable data, and other
        class-specific purity constraints.

        Args:
            node: AST class definition node to analyze.
        """
        if not self.is_pure_node:
            self.generic_visit(node)
            return

        prev_class = self.current_class
        self.current_class = node.name

        # Track @allow_dict_any on class level
        prev_class_allow_dict_any = self.class_allow_dict_any
        self.class_allow_dict_any = self._has_allow_dict_any_decorator(node)

        # Check if this is the node class (check inheritance)
        if self._is_node_class(node):
            self._check_inheritance(node)

        # Check for class-level mutable data in all classes
        self._check_class_attributes(node)

        self.generic_visit(node)
        self.current_class = prev_class
        self.class_allow_dict_any = prev_class_allow_dict_any

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for forbidden decorators and type hints.

        Args:
            node: AST function definition node to check.
        """
        self._check_decorators(node)

        # Check type hints in function signature if pure node
        if self.is_pure_node:
            has_allow_dict_any = self._has_allow_dict_any_decorator(node)
            self._check_function_type_hints(node, has_allow_dict_any)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definitions for forbidden decorators and type hints.

        Args:
            node: AST async function definition node to check.
        """
        self._check_decorators(node)

        # Check type hints in function signature if pure node
        if self.is_pure_node:
            has_allow_dict_any = self._has_allow_dict_any_decorator(node)
            self._check_function_type_hints(node, has_allow_dict_any)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check annotated assignments for Any/Dict[str, Any] type hints.

        Args:
            node: AST annotated assignment node to check.
        """
        if not self.is_pure_node:
            self.generic_visit(node)
            return

        # Skip if line is excluded or class has @allow_dict_any
        line_num = getattr(node, "lineno", 0)
        if self._is_line_excluded(line_num) or self.class_allow_dict_any:
            self.generic_visit(node)
            return

        # Check the annotation for Any/Dict[str, Any]
        self._check_type_annotation(node.annotation, node)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for forbidden operations.

        Detects forbidden filesystem operations, pathlib write methods,
        and other side-effect-producing function calls.

        Args:
            node: AST call node to check.
        """
        if not self.is_pure_node:
            self.generic_visit(node)
            return

        # Check for open() calls
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            # Check if mode argument suggests writing
            if self._is_write_mode_open(node):
                self._add_violation(
                    node,
                    ViolationType.OPEN_CALL,
                    Severity.ERROR,
                    "open() with write mode is forbidden in pure nodes",
                    "Use Effect nodes for file operations",
                )

        # Check for pathlib write methods
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_PATHLIB_METHODS:
                self._add_violation(
                    node,
                    ViolationType.PATHLIB_WRITE,
                    Severity.ERROR,
                    f"Path.{node.func.attr}() is forbidden in pure nodes",
                    "Use Effect nodes for filesystem modifications",
                )

        # Check for forbidden function calls
        func_name = self._get_call_name(node)
        if func_name in FORBIDDEN_FILESYSTEM_FUNCTIONS:
            self._add_violation(
                node,
                ViolationType.FILESYSTEM_OPERATION,
                Severity.ERROR,
                f"Filesystem operation '{func_name}' is forbidden in pure nodes",
                "Use Effect nodes for filesystem operations",
            )

        self.generic_visit(node)

    def _check_module_import(self, node: ast.AST, module_name: str) -> None:
        """Check if a module import is allowed in a pure node.

        Args:
            node: AST node for error location reporting.
            module_name: Fully qualified module name to check.
        """
        if not self.is_pure_node:
            return

        # Check networking
        if self._matches_forbidden_module(module_name, FORBIDDEN_NETWORKING_MODULES):
            self._add_violation(
                node,
                ViolationType.NETWORKING_IMPORT,
                Severity.ERROR,
                f"Networking module '{module_name}' is forbidden in pure nodes",
                "Use Effect nodes for network operations",
            )
            return

        # Check subprocess
        if self._matches_forbidden_module(module_name, FORBIDDEN_SUBPROCESS_MODULES):
            self._add_violation(
                node,
                ViolationType.SUBPROCESS_IMPORT,
                Severity.ERROR,
                f"Subprocess module '{module_name}' is forbidden in pure nodes",
                "Use Effect nodes for subprocess operations",
            )
            return

        # Check threading (special case: allowed in NodeCompute for ThreadPoolExecutor)
        if self._matches_forbidden_module(module_name, FORBIDDEN_THREADING_MODULES):
            # ThreadPoolExecutor is allowed in NodeCompute base class only
            if not (
                self.node_class_name == "NodeCompute"
                and module_name == "concurrent.futures"
            ):
                self._add_violation(
                    node,
                    ViolationType.THREADING_IMPORT,
                    Severity.ERROR,
                    f"Threading module '{module_name}' is forbidden in pure nodes",
                    "Pure nodes should not manage threads directly",
                )
            return

        # Check logging import at module level
        if module_name == "logging":
            self._add_violation(
                node,
                ViolationType.LOGGING_IMPORT,
                Severity.ERROR,
                "Module-level 'import logging' is forbidden",
                "Use structured logging via container.get_service('ProtocolLogger')",
            )
            return

        # Check if it's an allowed module
        if not self._is_allowed_module(module_name):
            self._add_violation(
                node,
                ViolationType.FORBIDDEN_IMPORT,
                Severity.WARNING,
                f"External module '{module_name}' may not be allowed in pure nodes",
                "Verify this module is needed and doesn't introduce side effects",
            )

    def _check_inheritance(self, node: ast.ClassDef) -> None:
        """Check that node class only inherits from allowed base classes.

        Args:
            node: AST class definition node to check.
        """
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name and base_name not in VALID_NODE_BASE_CLASSES:
                # Check if it's a Mixin (allowed)
                if not base_name.startswith("Mixin"):
                    self._add_violation(
                        node,
                        ViolationType.INVALID_INHERITANCE,
                        Severity.ERROR,
                        f"Invalid base class '{base_name}' for node",
                        f"Nodes must inherit from NodeCoreBase or allowed mixins. Found: {base_name}",
                    )

    def _check_class_attributes(self, node: ast.ClassDef) -> None:
        """Check for class-level mutable data that violates purity.

        Mutable class attributes (lists, dicts, sets) are forbidden
        because they introduce shared state between instances.

        Args:
            node: AST class definition node to check.
        """
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        # Skip dunder attributes and type annotations
                        if target.id.startswith("__"):
                            continue
                        # Check if value is mutable
                        if self._is_mutable_default(item.value):
                            self._add_violation(
                                item,
                                ViolationType.CLASS_MUTABLE_DATA,
                                Severity.ERROR,
                                f"Class-level mutable data '{target.id}' is forbidden",
                                "Use instance attributes in __init__ or make immutable (tuple, frozenset)",
                            )

            elif isinstance(item, ast.AnnAssign):
                if item.value and isinstance(item.target, ast.Name):
                    if not item.target.id.startswith("__"):
                        if self._is_mutable_default(item.value):
                            self._add_violation(
                                item,
                                ViolationType.CLASS_MUTABLE_DATA,
                                Severity.ERROR,
                                f"Class-level mutable data '{item.target.id}' is forbidden",
                                "Use instance attributes in __init__ or make immutable",
                            )

    def _check_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check function decorators for forbidden caching decorators.

        Caching decorators like @lru_cache introduce mutable state
        and are forbidden in pure nodes.

        Args:
            node: AST function definition node to check.
        """
        if not self.is_pure_node:
            return

        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if decorator_name in FORBIDDEN_CACHING_DECORATORS:
                self._add_violation(
                    decorator,
                    ViolationType.CACHING_DECORATOR,
                    Severity.ERROR,
                    f"Caching decorator '@{decorator_name}' introduces mutable state",
                    "Use ModelComputeCache from container or remove caching",
                )

    def _is_node_class(self, node: ast.ClassDef) -> bool:
        """Check if class is an ONEX Node class.

        Args:
            node: AST class definition node to check.

        Returns:
            True if class inherits from a Node base class.
        """
        # Check if it inherits from NodeCoreBase or Node* classes
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name in (
                "NodeCoreBase",
                "NodeCompute",
                "NodeEffect",
                "NodeReducer",
                "NodeOrchestrator",
            ):
                return True
            if base_name and base_name.startswith("Node"):
                return True
        return False

    def _determine_node_type(self, node: ast.ClassDef) -> str | None:
        """Determine the type of node from class name or base classes.

        Args:
            node: AST class definition node to analyze.

        Returns:
            Node type string ('compute', 'effect', 'reducer', 'orchestrator')
            or None if type cannot be determined.
        """
        class_name = node.name.lower()

        # Check class name
        if "compute" in class_name:
            return "compute"
        if "effect" in class_name:
            return "effect"
        if "reducer" in class_name:
            return "reducer"
        if "orchestrator" in class_name:
            return "orchestrator"

        # Check base classes
        for base in node.bases:
            base_name = self._get_base_name(base)
            if base_name:
                base_lower = base_name.lower()
                if "compute" in base_lower:
                    return "compute"
                if "effect" in base_lower:
                    return "effect"
                if "reducer" in base_lower:
                    return "reducer"
                if "orchestrator" in base_lower:
                    return "orchestrator"

        return None

    def _get_base_name(self, base: ast.expr) -> str | None:
        """Extract base class name from AST expression.

        Args:
            base: AST expression representing a base class.

        Returns:
            String name of the base class, or None if cannot be extracted.
        """
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        if isinstance(base, ast.Subscript):
            # Generic[T] case
            if isinstance(base.value, ast.Name):
                return base.value.id
        return None

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract decorator name from AST expression.

        Args:
            decorator: AST expression representing a decorator.

        Returns:
            String name of the decorator, or empty string if cannot be extracted.
        """
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            return decorator.attr
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract function name from call node.

        Args:
            node: AST call node to analyze.

        Returns:
            String name of the called function, or empty string if cannot be extracted.
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            return node.func.attr
        return ""

    def _is_mutable_default(self, value: ast.expr) -> bool:
        """Check if a value is a mutable default (list, dict, set).

        Args:
            value: AST expression representing a default value.

        Returns:
            True if value is a mutable data structure.
        """
        if isinstance(value, ast.List):
            return True
        if isinstance(value, ast.Dict):
            return True
        if isinstance(value, ast.Set):
            return True
        if isinstance(value, ast.Call):
            # Check for list(), dict(), set() calls
            if isinstance(value.func, ast.Name):
                return value.func.id in ("list", "dict", "set")
        return False

    def _is_write_mode_open(self, node: ast.Call) -> bool:
        """Check if open() call is in write mode.

        Args:
            node: AST call node for an open() call.

        Returns:
            True if open() is called with write, append, or create mode.
        """
        # Check positional mode argument
        if len(node.args) >= 2:
            mode_arg = node.args[1]
            if isinstance(mode_arg, ast.Constant):
                mode = mode_arg.value
                if isinstance(mode, str) and any(c in mode for c in "wax+"):
                    return True

        # Check keyword mode argument
        for keyword in node.keywords:
            if keyword.arg == "mode":
                if isinstance(keyword.value, ast.Constant):
                    mode = keyword.value.value
                    if isinstance(mode, str) and any(c in mode for c in "wax+"):
                        return True

        return False

    def _matches_forbidden_module(
        self, module_name: str, forbidden_set: frozenset[str]
    ) -> bool:
        """Check if module matches any forbidden module.

        Args:
            module_name: Fully qualified module name to check.
            forbidden_set: Set of forbidden module names/prefixes.

        Returns:
            True if module is in the forbidden set or matches a prefix.
        """
        if module_name in forbidden_set:
            return True
        # Check prefixes
        for forbidden in forbidden_set:
            if module_name.startswith(forbidden + "."):
                return True
        return False

    def _is_allowed_module(self, module_name: str) -> bool:
        """Check if module is in the allowed list for pure nodes.

        Args:
            module_name: Fully qualified module name to check.

        Returns:
            True if module is allowed (stdlib pure modules or framework).
        """
        # Check stdlib
        root_module = module_name.split(".")[0]
        if (
            root_module in ALLOWED_STDLIB_MODULES
            or module_name in ALLOWED_STDLIB_MODULES
        ):
            return True

        # Check framework prefixes
        for prefix in ALLOWED_FRAMEWORK_PREFIXES:
            if module_name.startswith(prefix):
                return True

        return False

    def _add_violation(
        self,
        node: ast.AST,
        violation_type: ViolationType,
        severity: Severity,
        message: str,
        suggestion: str,
    ) -> None:
        """Add a violation to the list.

        Args:
            node: AST node where violation was detected.
            violation_type: Type of purity violation.
            severity: Severity level (ERROR or WARNING).
            message: Human-readable description of the violation.
            suggestion: Suggested fix for the violation.
        """
        line_number = getattr(node, "lineno", 0)
        column = getattr(node, "col_offset", 0)

        # Get code snippet
        code_snippet = ""
        if line_number > 0 and line_number <= len(self.source_lines):
            code_snippet = self.source_lines[line_number - 1].strip()

        self.violations.append(
            PurityViolation(
                file_path=self.file_path,
                line_number=line_number,
                column=column,
                violation_type=violation_type,
                severity=severity,
                message=message,
                suggestion=suggestion,
                code_snippet=code_snippet,
            )
        )

    # ==========================================================================
    # OMN-203: DECLARATIVE NODE PURITY HELPER METHODS
    # ==========================================================================

    def _parse_onex_exclude_comments(self) -> None:
        """Parse source lines for ONEX_EXCLUDE comments.

        Identifies lines that have ONEX_EXCLUDE comments to exclude them
        from Any/Dict[str, Any] checks.
        """
        import re

        for i, line in enumerate(self.source_lines):
            # Check for ONEX_EXCLUDE comments
            if "ONEX_EXCLUDE:" in line:
                # The comment affects the next non-blank line (for function/class definitions)
                # or the current line (for inline exclusions)
                if re.search(r"#\s*ONEX_EXCLUDE:", line):
                    # Mark this line and next few lines as excluded
                    self.excluded_lines.add(i + 1)  # Current line (1-indexed)
                    # Also check if this is a comment-only line (marks next statement)
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        # This is a comment-only line, mark next few lines
                        for j in range(i + 1, min(i + 5, len(self.source_lines))):
                            next_line = self.source_lines[j].strip()
                            if next_line and not next_line.startswith("#"):
                                self.excluded_lines.add(j + 1)  # 1-indexed
                                break

    def _is_line_excluded(self, line_num: int) -> bool:
        """Check if a line is excluded from checks via ONEX_EXCLUDE.

        Args:
            line_num: Line number (1-indexed) to check.

        Returns:
            True if line is excluded from Any/Dict[Any] checks.
        """
        return line_num in self.excluded_lines

    def _is_type_checking_block(self, node: ast.If) -> bool:
        """Check if an If statement is a TYPE_CHECKING block.

        Args:
            node: AST If node to check.

        Returns:
            True if this is a `if TYPE_CHECKING:` block.
        """
        test = node.test
        # Handle: if TYPE_CHECKING:
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        # Handle: if typing.TYPE_CHECKING:
        if isinstance(test, ast.Attribute):
            if test.attr == "TYPE_CHECKING":
                return True
        return False

    def _has_allow_dict_any_decorator(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
    ) -> bool:
        """Check if a function or class has @allow_dict_any decorator.

        Args:
            node: AST function/class definition node.

        Returns:
            True if decorated with @allow_dict_any or @allow_dict_str_any.
        """
        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if decorator_name in ALLOW_DICT_ANY_DECORATORS:
                return True
        return False

    def _check_event_bus_module_import(self, node: ast.AST, module_name: str) -> None:
        """Check if a module import is from forbidden event bus modules.

        Args:
            node: AST node for error location reporting.
            module_name: Fully qualified module name to check.
        """
        if not self.is_pure_node:
            return

        # Check if module matches any forbidden event bus module prefix
        for forbidden_module in FORBIDDEN_EVENT_BUS_MODULES:
            if module_name == forbidden_module or module_name.startswith(
                forbidden_module + "."
            ):
                self._add_violation(
                    node,
                    ViolationType.EVENT_BUS_IMPORT,
                    Severity.ERROR,
                    f"Event bus module '{module_name}' is forbidden in declarative nodes",
                    "Use Effect nodes for event bus operations or emit intents instead",
                )
                return

    def _check_legacy_mixin_module_import(
        self, node: ast.AST, module_name: str
    ) -> None:
        """Check if a module import is a forbidden legacy mixin module.

        Detects imports like: import omnibase_core.mixins.mixin_event_bus

        Args:
            node: AST node for error location reporting.
            module_name: Fully qualified module name to check.
        """
        if not self.is_pure_node:
            return

        # Check if module path contains a forbidden mixin
        # e.g., omnibase_core.mixins.mixin_event_bus -> MixinEventBus
        for mixin_name in FORBIDDEN_LEGACY_MIXINS:
            # Convert MixinEventBus to mixin_event_bus pattern
            snake_case = self._camel_to_snake(mixin_name)
            if f"mixins.{snake_case}" in module_name or f".{snake_case}" in module_name:
                self._add_violation(
                    node,
                    ViolationType.LEGACY_MIXIN_IMPORT,
                    Severity.ERROR,
                    f"Legacy mixin module '{module_name}' is forbidden in declarative nodes",
                    "Remove mixin or use Effect nodes for event-driven functionality",
                )
                return

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case.

        Args:
            name: CamelCase name to convert.

        Returns:
            snake_case version of the name.
        """
        import re

        # Insert underscore before uppercase letters and convert to lowercase
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _check_function_type_hints(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        has_allow_dict_any: bool,
    ) -> None:
        """Check function parameter and return type hints for Any/Dict[str, Any].

        Args:
            node: AST function definition node.
            has_allow_dict_any: Whether function has @allow_dict_any decorator.
        """
        # Skip if function has @allow_dict_any or class has it
        if has_allow_dict_any or self.class_allow_dict_any:
            return

        line_num = getattr(node, "lineno", 0)
        if self._is_line_excluded(line_num):
            return

        # Check parameter annotations
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.annotation:
                self._check_type_annotation(arg.annotation, node)

        # Check *args annotation
        if node.args.vararg and node.args.vararg.annotation:
            self._check_type_annotation(node.args.vararg.annotation, node)

        # Check **kwargs annotation
        if node.args.kwarg and node.args.kwarg.annotation:
            self._check_type_annotation(node.args.kwarg.annotation, node)

        # Check return annotation
        if node.returns:
            self._check_type_annotation(node.returns, node)

    def _check_type_annotation(
        self, annotation: ast.expr, context_node: ast.AST
    ) -> None:
        """Check a type annotation for Any or Dict[str, Any] usage.

        Args:
            annotation: AST expression representing the type annotation.
            context_node: AST node to use for error location reporting.
        """
        # Check for bare "Any" name
        if isinstance(annotation, ast.Name) and annotation.id == "Any":
            self._add_violation(
                context_node,
                ViolationType.ANY_TYPE_HINT,
                Severity.ERROR,
                "'Any' type hint is forbidden in declarative nodes",
                "Use specific types, Generic type variables, or Pydantic models",
            )
            return

        # Check for typing.Any attribute access
        if isinstance(annotation, ast.Attribute) and annotation.attr == "Any":
            self._add_violation(
                context_node,
                ViolationType.ANY_TYPE_HINT,
                Severity.ERROR,
                "'typing.Any' type hint is forbidden in declarative nodes",
                "Use specific types, Generic type variables, or Pydantic models",
            )
            return

        # Check for subscripted types (Dict[str, Any], List[Any], etc.)
        if isinstance(annotation, ast.Subscript):
            # Check if this is Dict[str, Any] or dict[str, Any]
            if self._is_dict_str_any(annotation):
                self._add_violation(
                    context_node,
                    ViolationType.DICT_ANY_TYPE_HINT,
                    Severity.ERROR,
                    "'Dict[str, Any]' type hint is forbidden in declarative nodes",
                    "Use TypedDict, Pydantic models, or specific typed mappings",
                )
                return

            # Recursively check type arguments for Any
            self._check_subscript_for_any(annotation, context_node)
            return

        # Handle ast.List for Callable argument lists (e.g., Callable[[Any], str])
        # When processing Callable[[Any], str], the slice is a Tuple where the first
        # element is an ast.List containing the argument types
        if isinstance(annotation, ast.List):
            for elt in annotation.elts:
                self._check_type_annotation(elt, context_node)
            return

    def _is_dict_str_any(self, node: ast.Subscript) -> bool:
        """Check if a subscript is Dict[str, Any] or dict[str, Any].

        Args:
            node: AST subscript node to check.

        Returns:
            True if this is a Dict[str, Any] pattern.
        """
        # Check if the base is Dict or dict
        base = node.value
        is_dict_type = False

        if (isinstance(base, ast.Name) and base.id in ("Dict", "dict")) or (
            isinstance(base, ast.Attribute) and base.attr == "Dict"
        ):
            is_dict_type = True

        if not is_dict_type:
            return False

        # Check if slice is [str, Any]
        slice_node = node.slice

        # Python 3.9+ uses direct tuple for multiple args
        if isinstance(slice_node, ast.Tuple):
            elts = slice_node.elts
            if len(elts) == 2:
                # Check if second element is Any
                second = elts[1]
                if isinstance(second, ast.Name) and second.id == "Any":
                    return True
                if isinstance(second, ast.Attribute) and second.attr == "Any":
                    return True

        return False

    def _check_subscript_for_any(
        self, node: ast.Subscript, context_node: ast.AST
    ) -> None:
        """Recursively check subscript type arguments for Any usage.

        Args:
            node: AST subscript node to check.
            context_node: AST node to use for error location reporting.
        """
        slice_node = node.slice

        # Handle tuple of type arguments (e.g., Dict[K, V], Callable[[Args], Return])
        if isinstance(slice_node, ast.Tuple):
            for elt in slice_node.elts:
                self._check_type_annotation(elt, context_node)
        elif isinstance(slice_node, ast.List):
            # Callable[[arg_types], return_type] has a list for arg_types
            for elt in slice_node.elts:
                self._check_type_annotation(elt, context_node)
        else:
            # Single type argument (e.g., List[T], Optional[T])
            self._check_type_annotation(slice_node, context_node)


# ==============================================================================
# MAIN ANALYSIS FUNCTIONS
# ==============================================================================


# Base node files that are exempt from purity checks (framework code)
# These files legitimately need Any for generic type parameters
BASE_NODE_FILES_SKIP = {
    "node_compute.py",  # Base class needs Any for ModelComputeInput[Any]
    "node_reducer.py",  # Base class needs Any for generic type handling
}


def analyze_file(file_path: Path) -> PurityCheckResult:
    """
    Analyze a single file for purity violations.

    Uses a two-pass approach:
    1. First pass: Determine if file contains pure node classes
    2. Second pass: Check for purity violations if pure nodes found

    Args:
        file_path: Path to the Python file

    Returns:
        PurityCheckResult with violations and analysis
    """
    # Skip base node files (framework code with legitimate Any usage)
    if file_path.name in BASE_NODE_FILES_SKIP:
        return PurityCheckResult(
            file_path=file_path,
            node_class_name=None,
            node_type=None,
            violations=[],
            is_pure=True,
            skip_reason="Base node file (framework code with legitimate generic types)",
        )

    try:
        source = file_path.read_text(encoding="utf-8")
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=str(file_path))

        # First pass: Find node classes and determine if file contains pure nodes
        finder = NodeTypeFinder()
        finder.visit(tree)

        # Only report if this is a pure node
        if not finder.is_pure_node:
            return PurityCheckResult(
                file_path=file_path,
                node_class_name=finder.node_class_name,
                node_type=finder.node_type,
                violations=[],
                is_pure=True,
                skip_reason="Not a pure node (EFFECT/ORCHESTRATOR or not a node file)",
            )

        # Second pass: Analyze for purity violations with knowledge of node type
        analyzer = PurityAnalyzer(
            file_path=file_path,
            source_lines=source_lines,
            node_type=finder.node_type,
            node_class_name=finder.node_class_name,
            is_pure_node=finder.is_pure_node,
        )
        analyzer.visit(tree)

        # Filter violations by severity for is_pure calculation
        error_violations = [
            v for v in analyzer.violations if v.severity == Severity.ERROR
        ]

        return PurityCheckResult(
            file_path=file_path,
            node_class_name=analyzer.node_class_name,
            node_type=analyzer.node_type,
            violations=analyzer.violations,
            is_pure=len(error_violations) == 0,
            skip_reason=None,
        )

    except SyntaxError as e:
        return PurityCheckResult(
            file_path=file_path,
            node_class_name=None,
            node_type=None,
            violations=[
                PurityViolation(
                    file_path=file_path,
                    line_number=e.lineno or 0,
                    column=e.offset or 0,
                    violation_type=ViolationType.FORBIDDEN_IMPORT,
                    severity=Severity.ERROR,
                    message=f"Syntax error: {e.msg}",
                    suggestion="Fix the syntax error",
                )
            ],
            is_pure=False,
            skip_reason=f"Syntax error: {e.msg}",
        )
    except Exception as e:
        return PurityCheckResult(
            file_path=file_path,
            node_class_name=None,
            node_type=None,
            violations=[],
            is_pure=False,
            skip_reason=f"Error analyzing file: {e}",
        )


def find_node_files(src_dir: Path) -> list[Path]:
    """Find all node files to analyze.

    Searches for Python files matching the node_*.py pattern in the
    nodes/ and infrastructure/ directories.

    Args:
        src_dir: Source directory to search (typically src/omnibase_core).

    Returns:
        Sorted list of paths to node files.
    """
    node_files: list[Path] = []

    # Primary node implementations
    nodes_dir = src_dir / "nodes"
    if nodes_dir.exists():
        for py_file in nodes_dir.glob("node_*.py"):
            if py_file.name != "__init__.py":
                node_files.append(py_file)

    # Infrastructure nodes
    infra_dir = src_dir / "infrastructure"
    if infra_dir.exists():
        for py_file in infra_dir.glob("node_*.py"):
            node_files.append(py_file)

    return sorted(node_files)


def _safe_relative_path(file_path: Path, base_dir: Path) -> str:
    """Get relative path, falling back to full path if not relative.

    Args:
        file_path: Path to make relative.
        base_dir: Base directory to compute relative path from.

    Returns:
        String representation of relative path, or full path if relative_to fails.
    """
    try:
        return str(file_path.relative_to(base_dir))
    except ValueError:
        # Path is outside base_dir, return the full path
        return str(file_path)


def main() -> int:
    """Main entry point for the node purity validation script.

    Parses command line arguments, finds node files, runs purity analysis,
    and reports results.

    Returns:
        Exit code:
        - 0: All nodes pass purity checks
        - 1: Purity violations detected
        - 2: Script error (invalid arguments, file not found, etc.)
    """
    parser = argparse.ArgumentParser(
        description="Validate ONEX node purity guarantees using AST analysis"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with code snippets",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (stricter checking)",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Check a specific file instead of all node files",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=None,
        help="Source directory (default: src/omnibase_core)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Determine source directory
    if args.src_dir:
        src_dir = args.src_dir
    else:
        cwd = Path.cwd()
        src_dir = cwd / "src" / "omnibase_core"

        if not src_dir.exists():
            script_dir = Path(__file__).parent
            src_dir = script_dir.parent / "src" / "omnibase_core"

    if not src_dir.exists():
        print(f"Error: Source directory not found: {src_dir}", file=sys.stderr)
        return 2

    # Find files to analyze
    if args.file:
        if not args.file.exists():
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            return 2
        node_files = [args.file]
    else:
        node_files = find_node_files(src_dir)

    if not node_files:
        print("No node files found to analyze")
        return 0

    if args.verbose:
        print(f"Analyzing {len(node_files)} node files in {src_dir}")
        print()

    # Analyze each file
    results: list[PurityCheckResult] = []
    for file_path in node_files:
        result = analyze_file(file_path)
        results.append(result)

    # Output results
    if args.json:
        import json

        output = {
            "summary": {
                "total_files": len(results),
                "pure_files": sum(1 for r in results if r.is_pure),
                "impure_files": sum(1 for r in results if not r.is_pure),
            },
            "results": [
                {
                    "file": str(r.file_path),
                    "node_class": r.node_class_name,
                    "node_type": r.node_type,
                    "is_pure": r.is_pure,
                    "skip_reason": r.skip_reason,
                    "violations": [
                        {
                            "line": v.line_number,
                            "column": v.column,
                            "type": v.violation_type.value,
                            "severity": v.severity.value,
                            "message": v.message,
                            "suggestion": v.suggestion,
                        }
                        for v in r.violations
                    ],
                }
                for r in results
            ],
        }
        print(json.dumps(output, indent=2))
        return 0 if all(r.is_pure for r in results) else 1

    # Text output
    error_violations_found = False
    warning_violations_found = False

    for result in results:
        if result.skip_reason and args.verbose:
            relative_path = _safe_relative_path(result.file_path, src_dir.parent.parent)
            print(f"SKIP: {relative_path} - {result.skip_reason}")
            continue

        # Check for errors and warnings
        error_violations = [
            v for v in result.violations if v.severity == Severity.ERROR
        ]
        warning_violations = [
            v for v in result.violations if v.severity == Severity.WARNING
        ]

        if error_violations:
            error_violations_found = True
        if warning_violations:
            warning_violations_found = True

        # Only print if there are displayable violations
        displayable = error_violations + (warning_violations if args.strict else [])
        if displayable:
            relative_path = _safe_relative_path(result.file_path, src_dir.parent.parent)
            print(f"\nFile: {relative_path}")
            print(f"  Node: {result.node_class_name} ({result.node_type})")
            print()

            for violation in displayable:
                print(violation.format(args.verbose))

    # Summary
    pure_count = sum(1 for r in results if r.is_pure)
    impure_count = len(results) - pure_count
    analyzed_count = sum(1 for r in results if not r.skip_reason)

    print()
    print("=" * 60)
    print("Node Purity Check Summary")
    print("=" * 60)
    print(f"  Total files scanned: {len(results)}")
    print(f"  Pure node files analyzed: {analyzed_count}")
    print(f"  Pure: {pure_count}")
    print(f"  Impure: {impure_count}")

    # Determine exit status based on violations
    # In strict mode, warnings also cause failure
    should_fail = error_violations_found or (args.strict and warning_violations_found)

    if should_fail:
        print()
        print("FAILED: Purity violations detected")
        print("Fix the violations above to ensure declarative nodes remain pure.")
        return 1

    if warning_violations_found:
        print()
        print("PASSED with warnings: Run with --strict to treat warnings as errors")

    print()
    print("PASSED: All pure nodes maintain purity guarantees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
