#!/usr/bin/env python3
"""
ONEX Direct I/O Detection in Declarative Nodes.

Validates that declarative nodes (NodeCompute, NodeReducer, NodeOrchestrator)
do NOT contain direct I/O operations. Direct I/O should be handled by:
- NodeEffect for I/O operations
- Handlers in omnibase_infra for infrastructure concerns

FORBIDDEN I/O PATTERNS:
- File I/O: open(), Path.read_text(), Path.write_text(), pathlib I/O methods
- Network I/O: requests.*, httpx.*, aiohttp.*, urllib.request.*
- Database I/O: asyncpg.connect, psycopg2.connect, sqlite3.connect
- Message Queue I/O: confluent_kafka.*, kafka-python
- Environment Variables: os.environ[], os.getenv() (use config injection)

ALLOWED:
- NodeEffect (designed for I/O operations)
- Files with "# io-ok: <reason>" comment
- Test files
- Legacy node directory (nodes/legacy/)

Usage:
    # Check declarative nodes
    poetry run python scripts/validation/validate-no-direct-io.py

    # Check with verbose output
    poetry run python scripts/validation/validate-no-direct-io.py --verbose

Exit Codes:
    0: No violations found
    1: Direct I/O patterns found in declarative nodes
    2: Script error (invalid arguments, file not found, etc.)
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Final, NamedTuple


class IOViolation(NamedTuple):
    """Represents a direct I/O violation in a declarative node."""

    file_path: str
    line_number: int
    column: int
    pattern_type: str
    code_snippet: str
    description: str


# Bypass pattern for intentionally allowed I/O
BYPASS_PATTERNS: Final[list[str]] = [
    "io-ok:",
]

# Files that are allowed to have direct I/O
ALLOWED_FILES: Final[list[str]] = [
    "node_effect.py",  # NodeEffect is designed for I/O operations
]

# Directory patterns to exclude
EXCLUDED_DIRS: Final[list[str]] = [
    "legacy",
    "tests",
    "__pycache__",
]


class DirectIODetector(ast.NodeVisitor):
    """AST visitor to detect direct I/O patterns in Python code."""

    def __init__(self, file_path: str, file_content: str) -> None:
        self.file_path = file_path
        self.file_content = file_content
        self.lines = file_content.splitlines()
        self.violations: list[IOViolation] = []

        # Track imports for qualified name detection
        self.imported_modules: dict[str, str] = {}
        self.from_imports: dict[str, str] = {}

        # File I/O function names
        self.file_io_funcs: set[str] = {"open"}

        # Path methods that perform I/O
        self.path_io_methods: set[str] = {
            "read_text",
            "read_bytes",
            "write_text",
            "write_bytes",
            "open",
            "unlink",
            "rmdir",
            "mkdir",
            "touch",
            "rename",
            "replace",
            "chmod",
            "stat",
            "lstat",
            "exists",
            "is_file",
            "is_dir",
            "iterdir",
            "glob",
            "rglob",
        }

        # Network I/O module patterns
        self.network_io_modules: set[str] = {
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
        }

        # Network I/O methods
        self.network_io_methods: set[str] = {
            "get",
            "post",
            "put",
            "delete",
            "patch",
            "head",
            "options",
            "request",
        }

        # Database connection functions
        self.db_connect_funcs: set[str] = {
            "connect",
            "create_engine",
            "create_async_engine",
        }

        # Database modules
        self.db_modules: set[str] = {
            "asyncpg",
            "psycopg2",
            "psycopg",
            "sqlite3",
            "sqlalchemy",
            "pymysql",
            "mysql",
        }

        # Kafka/message queue modules
        self.mq_modules: set[str] = {
            "confluent_kafka",
            "kafka",
            "aiokafka",
            "pika",
            "aio_pika",
        }

        # Environment variable access patterns
        self.env_var_attrs: set[str] = {"environ"}
        self.env_var_funcs: set[str] = {"getenv"}

    def _get_line_content(self, lineno: int) -> str:
        """Get the content of a specific line."""
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def _add_violation(
        self,
        lineno: int,
        col_offset: int,
        pattern_type: str,
        description: str,
    ) -> None:
        """Add a violation to the list."""
        code_snippet = self._get_line_content(lineno)
        self.violations.append(
            IOViolation(
                file_path=self.file_path,
                line_number=lineno,
                column=col_offset,
                pattern_type=pattern_type,
                code_snippet=code_snippet,
                description=description,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:
        """Track imports for qualified name detection."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imported_modules[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from imports for qualified name detection."""
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.from_imports[name] = full_name
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for I/O patterns."""
        # Check for direct open() calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.file_io_funcs:
                self._add_violation(
                    node.lineno,
                    node.col_offset,
                    "file_io",
                    f"Direct file I/O: {func_name}() - use NodeEffect or handler",
                )
            elif func_name in self.env_var_funcs:
                self._add_violation(
                    node.lineno,
                    node.col_offset,
                    "env_var",
                    f"Direct env var access: {func_name}() - use config injection",
                )

        # Check for method calls on objects
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr

            # Check for Path I/O methods
            if attr_name in self.path_io_methods:
                # Try to determine if this is a Path object
                if self._is_likely_path_object(node.func.value):
                    self._add_violation(
                        node.lineno,
                        node.col_offset,
                        "path_io",
                        f"Path I/O operation: .{attr_name}() - use NodeEffect or handler",
                    )

            # Check for network I/O methods
            if attr_name in self.network_io_methods:
                if self._is_network_module_call(node.func.value):
                    self._add_violation(
                        node.lineno,
                        node.col_offset,
                        "network_io",
                        f"Network I/O: .{attr_name}() - use NodeEffect or handler",
                    )

            # Check for database connections
            if attr_name in self.db_connect_funcs:
                if self._is_db_module_call(node.func.value):
                    self._add_violation(
                        node.lineno,
                        node.col_offset,
                        "database_io",
                        f"Database I/O: .{attr_name}() - use NodeEffect or handler",
                    )

            # Check for env var access via os.getenv
            if attr_name in self.env_var_funcs:
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                    self._add_violation(
                        node.lineno,
                        node.col_offset,
                        "env_var",
                        f"Direct env var access: os.{attr_name}() - use config injection",
                    )

            # Check for Kafka/MQ usage
            if self._is_mq_module_call(node.func.value):
                self._add_violation(
                    node.lineno,
                    node.col_offset,
                    "message_queue_io",
                    f"Message queue I/O: .{attr_name}() - use NodeEffect or handler",
                )

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Check for os.environ[] access."""
        if isinstance(node.value, ast.Attribute):
            if (
                node.value.attr in self.env_var_attrs
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
            ):
                self._add_violation(
                    node.lineno,
                    node.col_offset,
                    "env_var",
                    "Direct env var access: os.environ[] - use config injection",
                )

        self.generic_visit(node)

    def _is_likely_path_object(self, node: ast.AST) -> bool:
        """Check if node is likely a Path object.

        This method uses conservative heuristics to minimize false positives:
        - Direct Path() constructor calls are definite matches
        - Chained Path methods (with_suffix, parent, etc.) indicate Path usage
        - Variable names are only matched when they clearly indicate path objects
          (e.g., file_path, config_dir) not just any name containing "path"

        NOTE: This check is called in the context of visit_Call, meaning we're
        already inside a method call like `node.read_text()`. The node parameter
        is the object being called on, NOT a type annotation.
        """
        # Direct Path() call - definite match
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "Path":
                return True
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "Path"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "pathlib"
            ):
                return True

        # Chained method call (e.g., file_path.with_suffix().read_text())
        # These are Path-specific methods that strongly indicate a Path object
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            path_methods = {"with_suffix", "with_name", "parent", "stem", "resolve"}
            if node.func.attr in path_methods:
                return True

        # Variable named with common path patterns
        # Use conservative matching to reduce false positives:
        # - Match names ending with _path, _file, _dir, _folder
        # - Match compound names like filepath, dirpath
        # - Match exact names like "path", "file", "directory"
        # - Do NOT match partial matches like "xpath" or "filepath_validator"
        if isinstance(node, ast.Name):
            name_lower = node.id.lower()
            # Exact match for simple names
            if name_lower in {"path", "file", "directory", "folder", "dir"}:
                return True
            # Names ending with path indicators (most common pattern)
            if name_lower.endswith(("_path", "_file", "_dir", "_folder", "_directory")):
                return True
            # Compound names without underscore (e.g., filepath, configdir)
            # Only match specific known patterns to avoid false positives
            compound_patterns = {
                "filepath",
                "dirpath",
                "folderpath",
                "configpath",
                "basepath",
                "rootpath",
                "srcpath",
                "configdir",
                "basedir",
                "rootdir",
                "srcdir",
                "configfile",
                "basefile",
                "rootfile",
                "srcfile",
            }
            if name_lower in compound_patterns:
                return True

        # Attribute access that might be a path
        # Use the same conservative matching for attribute names
        if isinstance(node, ast.Attribute):
            attr_lower = node.attr.lower()
            # Exact match for simple names
            if attr_lower in {"path", "file", "directory", "folder", "dir"}:
                return True
            # Names ending with path indicators
            if attr_lower.endswith(("_path", "_file", "_dir", "_folder", "_directory")):
                return True
            # Compound names without underscore (same logic as above)
            compound_patterns = {
                "filepath",
                "dirpath",
                "folderpath",
                "configpath",
                "basepath",
                "rootpath",
                "srcpath",
                "configdir",
                "basedir",
                "rootdir",
                "srcdir",
                "configfile",
                "basefile",
                "rootfile",
                "srcfile",
            }
            if attr_lower in compound_patterns:
                return True

        return False

    def _is_network_module_call(self, node: ast.AST) -> bool:
        """Check if node is a network module access.

        Handles both direct module access and aliased imports:
        - `requests.get()` - direct module access
        - `import requests as r; r.get()` - aliased import
        - `from requests import get; get()` - from import (handled elsewhere)
        """
        if isinstance(node, ast.Name):
            # Direct module name match
            if node.id in self.network_io_modules:
                return True
            # Check if this is an alias for a network module
            if node.id in self.imported_modules:
                original_module = self.imported_modules[node.id]
                if any(mod in original_module for mod in self.network_io_modules):
                    return True
            # Check from_imports for aliased imports
            if node.id in self.from_imports:
                full_name = self.from_imports[node.id]
                if any(mod in full_name for mod in self.network_io_modules):
                    return True
            return False

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return node.value.id in self.network_io_modules

        return False

    def _is_db_module_call(self, node: ast.AST) -> bool:
        """Check if node is a database module access.

        Handles both direct module access and aliased imports:
        - `asyncpg.connect()` - direct module access
        - `import asyncpg as db; db.connect()` - aliased import
        """
        if isinstance(node, ast.Name):
            # Direct module name match
            if node.id in self.db_modules:
                return True
            # Check if this is an alias for a database module
            if node.id in self.imported_modules:
                original_module = self.imported_modules[node.id]
                if any(mod in original_module for mod in self.db_modules):
                    return True
            # Check from_imports for aliased imports
            if node.id in self.from_imports:
                full_name = self.from_imports[node.id]
                if any(mod in full_name for mod in self.db_modules):
                    return True
            return False

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return node.value.id in self.db_modules

        return False

    def _is_mq_module_call(self, node: ast.AST) -> bool:
        """Check if node is a message queue module access.

        Handles both direct module access and aliased imports:
        - `confluent_kafka.Producer()` - direct module access
        - `import confluent_kafka as kafka; kafka.Producer()` - aliased import
        """
        if isinstance(node, ast.Name):
            # Direct module name match
            if node.id in self.mq_modules:
                return True
            # Check if this is an alias for a message queue module
            if node.id in self.imported_modules:
                original_module = self.imported_modules[node.id]
                if any(mod in original_module for mod in self.mq_modules):
                    return True
            # Check from_imports for aliased imports
            if node.id in self.from_imports:
                full_name = self.from_imports[node.id]
                if any(mod in full_name for mod in self.mq_modules):
                    return True
            return False

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return node.value.id in self.mq_modules

        return False

    def check_file(self) -> list[IOViolation]:
        """Parse and check the file for I/O violations.

        Note:
            Bypass comments (e.g., "# io-ok: reason") work at file-level only.
            If any bypass pattern is found anywhere in the file, the entire
            file is excluded from validation. This is simpler and more
            predictable than line-level bypass tracking.
        """
        # Check for file-level bypass - if present, skip entire file
        if any(pattern in self.file_content for pattern in BYPASS_PATTERNS):
            return []

        try:
            tree = ast.parse(self.file_content, filename=self.file_path)
            self.visit(tree)
        except SyntaxError:
            # Skip files with syntax errors
            pass

        return self.violations


class DirectIOValidator:
    """Validates that declarative nodes don't contain direct I/O."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.violations: list[IOViolation] = []
        self.checked_files: int = 0
        self.skipped_files: list[str] = []

    def validate_file(self, file_path: Path) -> bool:
        """Validate a single file for direct I/O patterns."""
        # Skip allowed files
        if file_path.name in ALLOWED_FILES:
            if self.verbose:
                self.skipped_files.append(f"{file_path} (allowed file)")
                print(f"  [SKIP] {file_path} (allowed file)")
            return True

        # Skip excluded directories
        for excluded_dir in EXCLUDED_DIRS:
            if excluded_dir in file_path.parts:
                if self.verbose:
                    self.skipped_files.append(f"{file_path} (excluded directory)")
                    print(f"  [SKIP] {file_path} (excluded directory: {excluded_dir})")
                return True

        if self.verbose:
            print(f"  [CHECK] {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            if self.verbose:
                print(f"  [ERROR] Could not read {file_path}: {e}")
            else:
                print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
            return True

        # Check for file-level bypass
        if any(pattern in content for pattern in BYPASS_PATTERNS):
            if self.verbose:
                self.skipped_files.append(f"{file_path} (bypass comment)")
                print(f"  [SKIP] {file_path} (bypass comment: io-ok)")
            return True

        self.checked_files += 1
        detector = DirectIODetector(str(file_path), content)
        file_violations = detector.check_file()
        self.violations.extend(file_violations)

        if self.verbose and file_violations:
            print(f"    -> Found {len(file_violations)} violation(s)")

        return len(file_violations) == 0

    def validate_directory(self, directory: Path) -> bool:
        """Validate all Python files in directory."""
        if self.verbose:
            print(f"Scanning directory: {directory}")
            print()

        all_valid = True

        for py_file in sorted(directory.rglob("*.py")):
            if not self.validate_file(py_file):
                all_valid = False

        if self.verbose:
            print()

        return all_valid

    def print_results(self) -> None:
        """Print validation results."""
        if self.verbose and self.skipped_files:
            print("\nSkipped files:")
            for skipped in self.skipped_files:
                print(f"  - {skipped}")
            print()

        if not self.violations:
            print(
                f"No direct I/O patterns found in declarative nodes "
                f"({self.checked_files} files checked)"
            )
            return

        print("=" * 80)
        print("DIRECT I/O PATTERNS FOUND IN DECLARATIVE NODES")
        print("=" * 80)
        print()
        print(
            f"Found {len(self.violations)} violation(s) in {self.checked_files} files:"
        )
        print()

        # Group violations by file
        violations_by_file: dict[str, list[IOViolation]] = {}
        for violation in self.violations:
            if violation.file_path not in violations_by_file:
                violations_by_file[violation.file_path] = []
            violations_by_file[violation.file_path].append(violation)

        # Print violations grouped by file
        for file_path in sorted(violations_by_file.keys()):
            file_violations = violations_by_file[file_path]
            print(f"{file_path}")
            for violation in sorted(file_violations, key=lambda v: v.line_number):
                print(
                    f"  Line {violation.line_number}:{violation.column} "
                    f"[{violation.pattern_type}]"
                )
                print(f"    {violation.description}")
                print(f"    Code: {violation.code_snippet}")
            print()

        print("=" * 80)
        print("HOW TO FIX:")
        print("=" * 80)
        print()
        print("1. Move I/O operations to NodeEffect handlers")
        print(
            "2. Use dependency injection for configuration (not os.environ/os.getenv)"
        )
        print("3. If intentional, add bypass comment: # io-ok: <reason>")
        print()
        print("ARCHITECTURE PRINCIPLE:")
        print("  - NodeCompute: Pure computation, no side effects")
        print("  - NodeReducer: FSM state management, no direct I/O")
        print("  - NodeOrchestrator: Workflow coordination, emits Actions")
        print("  - NodeEffect: Handles ALL I/O operations")
        print()


def main() -> int:
    """Main entry point for the validation script."""
    parser = argparse.ArgumentParser(
        description="Validate declarative nodes for direct I/O patterns"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--directory",
        "-d",
        type=str,
        default="src/omnibase_core/nodes",
        help="Directory to scan (default: src/omnibase_core/nodes)",
    )

    args = parser.parse_args()

    # Resolve directory path
    base_dir = Path(args.directory)
    if not base_dir.is_absolute():
        # Try to find the directory relative to script location or cwd
        script_dir = Path(__file__).parent.parent.parent
        if (script_dir / args.directory).exists():
            base_dir = script_dir / args.directory
        elif Path(args.directory).exists():
            base_dir = Path(args.directory)
        else:
            print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
            return 2

    if not base_dir.exists():
        print(f"Error: Directory not found: {base_dir}", file=sys.stderr)
        return 2

    if not base_dir.is_dir():
        print(f"Error: Not a directory: {base_dir}", file=sys.stderr)
        return 2

    validator = DirectIOValidator(verbose=args.verbose)
    success = validator.validate_directory(base_dir)
    validator.print_results()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
