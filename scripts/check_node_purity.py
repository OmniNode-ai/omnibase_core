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
FORBIDDEN_FILESYSTEM_FUNCTIONS = frozenset(
    {
        "open",  # Only when mode includes 'w', 'a', 'x', '+'
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
    """First pass: Find node classes and determine if file contains pure nodes."""

    def __init__(self) -> None:
        self.node_class_name: str | None = None
        self.node_type: str | None = None
        self.is_pure_node: bool = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Find node class definitions."""
        if self._is_node_class(node):
            self.node_class_name = node.name
            self.node_type = self._determine_node_type(node)
            self.is_pure_node = self.node_type in ("compute", "reducer")
        self.generic_visit(node)

    def _is_node_class(self, node: ast.ClassDef) -> bool:
        """Check if class is a Node class."""
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
        """Determine the type of node (compute, effect, reducer, orchestrator)."""
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
        """Extract base class name from AST node."""
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
    """AST visitor to analyze node purity (second pass)."""

    file_path: Path
    source_lines: list[str]
    violations: list[PurityViolation] = field(default_factory=list)
    node_type: str | None = None
    node_class_name: str | None = None
    is_pure_node: bool = False
    current_class: str | None = None

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements."""
        for alias in node.names:
            module_name = alias.name
            self._check_module_import(node, module_name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from ... import statements."""
        module_name = node.module or ""

        # Check the module itself
        self._check_module_import(node, module_name)

        # Check specific imports for caching decorators
        if self.is_pure_node:
            for alias in node.names:
                full_name = f"{module_name}.{alias.name}" if module_name else alias.name
                if (
                    alias.name in FORBIDDEN_CACHING_DECORATORS
                    or full_name in FORBIDDEN_CACHING_DECORATORS
                ):
                    self._add_violation(
                        node,
                        ViolationType.CACHING_DECORATOR,
                        Severity.ERROR,
                        f"Caching decorator '{alias.name}' introduces mutable state",
                        "Use container-provided caching services or ModelComputeCache",
                    )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Analyze class definitions for purity violations."""
        if not self.is_pure_node:
            self.generic_visit(node)
            return

        prev_class = self.current_class
        self.current_class = node.name

        # Check if this is the node class (check inheritance)
        if self._is_node_class(node):
            self._check_inheritance(node)

        # Check for class-level mutable data in all classes
        self._check_class_attributes(node)

        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for forbidden decorators."""
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definitions for forbidden decorators."""
        self._check_decorators(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for forbidden operations."""
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
        """Check if a module import is allowed."""
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
        """Check that node class only inherits from allowed base classes."""
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
        """Check for class-level mutable data."""
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
        """Check function decorators for forbidden caching decorators."""
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
        """Check if class is a Node class."""
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
        """Determine the type of node (compute, effect, reducer, orchestrator)."""
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
        """Extract base class name from AST node."""
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
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            return decorator.attr
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return ""

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract function name from call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            return node.func.attr
        return ""

    def _is_mutable_default(self, value: ast.expr) -> bool:
        """Check if a value is a mutable default (list, dict, set)."""
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
        """Check if open() call is in write mode."""
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
        """Check if module matches any forbidden module."""
        if module_name in forbidden_set:
            return True
        # Check prefixes
        for forbidden in forbidden_set:
            if module_name.startswith(forbidden + "."):
                return True
        return False

    def _is_allowed_module(self, module_name: str) -> bool:
        """Check if module is in the allowed list."""
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
        """Add a violation to the list."""
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


# ==============================================================================
# MAIN ANALYSIS FUNCTIONS
# ==============================================================================


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
    """
    Find all node files to analyze.

    Args:
        src_dir: Source directory to search

    Returns:
        List of node file paths
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


def main() -> int:
    """Main entry point."""
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
            relative_path = result.file_path.relative_to(src_dir.parent.parent)
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
            relative_path = result.file_path.relative_to(src_dir.parent.parent)
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
