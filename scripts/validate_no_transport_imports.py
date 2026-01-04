#!/usr/bin/env python3
"""AST-based validator for transport/I/O library imports in omnibase_core.

This script enforces the architectural boundary defined in ADR-005:
omnibase_core must be pure (no runtime I/O dependencies).

Unlike the grep-based predecessor, this script correctly detects and allows
imports inside TYPE_CHECKING blocks, which are legal per ADR-005 since they
create no runtime dependencies.

Usage:
    poetry run python scripts/validate_no_transport_imports.py
    poetry run python scripts/validate_no_transport_imports.py --verbose
    poetry run python scripts/validate_no_transport_imports.py --exclude path/to/file.py

Exit codes:
    0 = no violations
    1 = violations found
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

# Banned transport/I/O modules that cannot be imported at runtime in omnibase_core
# These create runtime dependencies on external I/O libraries
BANNED_MODULES: frozenset[str] = frozenset(
    {
        # HTTP clients
        "aiohttp",
        "httpx",
        "requests",
        "urllib3",
        # Kafka clients
        "kafka",
        "aiokafka",
        "confluent_kafka",
        # Redis clients
        "redis",
        "aioredis",
        # Database clients
        "asyncpg",
        "psycopg2",
        "psycopg",
        "aiomysql",
        # Message queues
        "pika",
        "aio_pika",
        "kombu",
        "celery",
        # gRPC (import name is "grpc", not "grpcio" which is the PyPI package name)
        "grpc",
        # WebSocket
        "websockets",
        "wsproto",
    }
)

# Directories to skip during traversal (standard Python/build artifacts)
SKIP_DIRECTORIES: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        ".env",
        "build",
        "dist",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".eggs",
        "*.egg-info",
    }
)


@dataclass(frozen=True)
class Violation:
    """Represents a banned import violation."""

    file_path: Path
    line_number: int
    module_name: str
    import_statement: str

    def __str__(self) -> str:
        return f"{self.file_path}:{self.line_number}: Banned transport import: {self.module_name}"


class TransportImportChecker(ast.NodeVisitor):
    """AST visitor that detects banned transport imports outside TYPE_CHECKING blocks.

    This visitor tracks:
    1. Imports of TYPE_CHECKING (direct or aliased like `import typing as t`)
    2. Entry/exit from TYPE_CHECKING guarded blocks
    3. All import statements, flagging those importing banned modules at runtime
    """

    def __init__(self, source_code: str) -> None:
        self.source_lines = source_code.splitlines()
        self.violations: list[Violation] = []
        self._in_type_checking_block = False
        self._type_checking_aliases: set[str] = set()

    def _get_source_line(self, lineno: int) -> str:
        """Get the source line for a given line number (1-indexed)."""
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""

    def _extract_root_module(self, module_name: str) -> str:
        """Extract the root module from a potentially dotted module path.

        Example: 'aiohttp.client' -> 'aiohttp'
        """
        return module_name.split(".")[0]

    def _is_type_checking_guard(self, node: ast.If) -> bool:
        """Detect if an If node is a TYPE_CHECKING guard.

        Handles:
        - `if TYPE_CHECKING:`
        - `if typing.TYPE_CHECKING:`
        - `if t.TYPE_CHECKING:` (when `import typing as t`)
        """
        test = node.test

        # Direct: if TYPE_CHECKING:
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True

        # Attribute: if typing.TYPE_CHECKING: or if t.TYPE_CHECKING:
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            # Check if it's typing.TYPE_CHECKING or an aliased version
            if isinstance(test.value, ast.Name):
                # typing.TYPE_CHECKING or aliased like t.TYPE_CHECKING
                if test.value.id == "typing" or test.value.id in self._type_checking_aliases:
                    return True
            return True  # Any X.TYPE_CHECKING is likely a TYPE_CHECKING guard

        return False

    def visit_Import(self, node: ast.Import) -> None:
        """Handle `import X` and `import X as Y` statements."""
        # Track typing module aliases: import typing as t
        for alias in node.names:
            if alias.name == "typing" and alias.asname:
                self._type_checking_aliases.add(alias.asname)

        # Check for banned imports (only if not in TYPE_CHECKING block)
        if not self._in_type_checking_block:
            for alias in node.names:
                root_module = self._extract_root_module(alias.name)
                if root_module in BANNED_MODULES:
                    self.violations.append(
                        Violation(
                            file_path=Path(),  # Will be set by caller
                            line_number=node.lineno,
                            module_name=root_module,
                            import_statement=self._get_source_line(node.lineno),
                        )
                    )

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle `from X import Y` statements."""
        if node.module is None:
            # Relative import without module (from . import X)
            self.generic_visit(node)
            return

        # Track TYPE_CHECKING imports: from typing import TYPE_CHECKING
        for alias in node.names:
            if alias.name == "TYPE_CHECKING":
                # If aliased, track the alias
                if alias.asname:
                    self._type_checking_aliases.add(alias.asname)

        # Check for banned imports (only if not in TYPE_CHECKING block)
        if not self._in_type_checking_block:
            root_module = self._extract_root_module(node.module)
            if root_module in BANNED_MODULES:
                self.violations.append(
                    Violation(
                        file_path=Path(),  # Will be set by caller
                        line_number=node.lineno,
                        module_name=root_module,
                        import_statement=self._get_source_line(node.lineno),
                    )
                )

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Handle If statements, detecting TYPE_CHECKING guards."""
        if self._is_type_checking_guard(node):
            # Mark that we're inside a TYPE_CHECKING block
            old_state = self._in_type_checking_block
            self._in_type_checking_block = True
            # Visit body of TYPE_CHECKING block
            for child in node.body:
                self.visit(child)
            self._in_type_checking_block = old_state
            # Visit else clause normally (not inside TYPE_CHECKING)
            for child in node.orelse:
                self.visit(child)
        else:
            # Normal If statement - visit all children
            self.generic_visit(node)


def iter_python_files(root_dir: Path, excludes: set[Path]) -> Iterator[Path]:
    """Iterate over all Python files in a directory, skipping excluded paths."""
    for path in root_dir.rglob("*.py"):
        # Skip files in excluded directories
        if any(skip_dir in path.parts for skip_dir in SKIP_DIRECTORIES):
            continue

        # Check against user-provided exclusions
        should_exclude = False
        for exclude_path in excludes:
            try:
                path.relative_to(exclude_path)
                should_exclude = True
                break
            except ValueError:
                # path is not relative to exclude_path
                if exclude_path.name == path.name or str(exclude_path) in str(path):
                    should_exclude = True
                    break

        if not should_exclude:
            yield path


def check_file(file_path: Path) -> list[Violation]:
    """Check a single Python file for banned transport imports.

    Returns a list of violations found in the file.
    """
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return []

    try:
        tree = ast.parse(source_code, filename=str(file_path))
    except SyntaxError as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return []

    checker = TransportImportChecker(source_code)
    checker.visit(tree)

    # Update file paths in violations
    violations = []
    for v in checker.violations:
        violations.append(
            Violation(
                file_path=file_path,
                line_number=v.line_number,
                module_name=v.module_name,
                import_statement=v.import_statement,
            )
        )

    return violations


def main() -> int:
    """Main entry point for the validator."""
    parser = argparse.ArgumentParser(
        description="Validate no banned transport/I/O imports in omnibase_core",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Banned modules:
  HTTP: aiohttp, httpx, requests, urllib3
  Kafka: kafka, aiokafka, confluent_kafka
  Redis: redis, aioredis
  Database: asyncpg, psycopg2, psycopg, aiomysql
  MQ: pika, aio_pika, kombu, celery
  gRPC: grpc
  WebSocket: websockets, wsproto

TYPE_CHECKING guarded imports are allowed per ADR-005.
""",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=Path("src/omnibase_core"),
        help="Source directory to scan (default: src/omnibase_core)",
    )
    parser.add_argument(
        "--exclude",
        type=Path,
        action="append",
        default=[],
        dest="excludes",
        metavar="PATH",
        help="Exclude a file or directory (can be specified multiple times)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show import statement snippets for each violation",
    )

    args = parser.parse_args()

    # Validate source directory exists
    src_dir = args.src_dir
    if not src_dir.exists():
        print(f"Error: Source directory does not exist: {src_dir}", file=sys.stderr)
        return 1

    if not src_dir.is_dir():
        print(f"Error: Source path is not a directory: {src_dir}", file=sys.stderr)
        return 1

    # Collect all violations
    excludes = set(args.excludes)
    all_violations: list[Violation] = []
    file_count = 0

    print(f"Checking for transport/I/O library imports in {src_dir}...")

    for file_path in iter_python_files(src_dir, excludes):
        file_count += 1
        violations = check_file(file_path)
        all_violations.extend(violations)

    if all_violations:
        print("\nERROR: Found transport/I/O library imports in omnibase_core!")
        print()
        print("Violations:")
        for v in all_violations:
            print(f"  {v}")
            if args.verbose:
                print(f"    -> {v.import_statement}")
        print()
        print("Architectural Invariant: omnibase_core must be pure (no I/O dependencies).")
        print("Transport and I/O libraries belong in infrastructure layers.")
        print()
        print("Solutions:")
        print("  1. Define a protocol in omnibase_core for the capability you need")
        print("  2. Implement the protocol in an infrastructure package")
        print("  3. Use TYPE_CHECKING guards for type-only imports (allowed per ADR-005)")
        print()
        print(f"Total: {len(all_violations)} violation(s) in {file_count} files scanned")
        return 1

    print(f"No transport/I/O library imports found in omnibase_core ({file_count} files scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
