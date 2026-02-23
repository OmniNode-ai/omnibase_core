#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST-based validator for transport/I/O library imports in omnibase_core.

This script enforces the architectural boundary defined in ADR-005:
omnibase_core must be pure (no runtime I/O dependencies).

Unlike the grep-based predecessor, this script correctly detects and allows
imports inside TYPE_CHECKING blocks, which are legal per ADR-005 since they
create no runtime dependencies.

Usage:
    uv run python scripts/validate_no_transport_imports.py
    uv run python scripts/validate_no_transport_imports.py --verbose
    uv run python scripts/validate_no_transport_imports.py --exclude path/to/file.py

Exit codes:
    0 = no violations
    1 = violations found
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class FileProcessingError:
    """Represents an error encountered while processing a file.

    These are non-fatal warnings that indicate a file could not be fully processed,
    but should not fail the overall validation run (errors do not cause exit code 1).
    """

    file_path: Path
    error_type: str
    error_message: str

    def __str__(self) -> str:
        return f"{self.file_path}: [{self.error_type}] {self.error_message}"


class TransportImportChecker(ast.NodeVisitor):
    """AST visitor that detects banned transport imports outside TYPE_CHECKING blocks.

    This visitor tracks:
    1. Imports of TYPE_CHECKING (direct or aliased like `import typing as t`)
    2. Entry/exit from TYPE_CHECKING guarded blocks
    3. All import statements, flagging those importing banned modules at runtime

    Thread Safety:
        This class is NOT thread-safe. Each thread should create its own instance.
        The instance maintains mutable state (violations list, type_checking context)
        that is not synchronized.
    """

    def __init__(self, source_code: str) -> None:
        self.source_lines = source_code.splitlines()
        self.violations: list[Violation] = []
        self._in_type_checking_block = False
        # Module aliases (e.g., "t" from `import typing as t`)
        # These are ONLY valid in attribute access: `if t.TYPE_CHECKING:`
        # NOT valid as direct names: `if t:` is NOT a TYPE_CHECKING guard
        self._type_checking_module_aliases: set[str] = set()
        # Constant aliases (e.g., "TC" from `from typing import TYPE_CHECKING as TC`)
        # These ARE valid as direct names: `if TC:` is a TYPE_CHECKING guard
        self._type_checking_constant_aliases: set[str] = set()

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
        - `if TYPE_CHECKING:` (direct import)
        - `if TC:` (when `from typing import TYPE_CHECKING as TC`)
        - `if typing.TYPE_CHECKING:` (module-qualified)
        - `if t.TYPE_CHECKING:` (when `import typing as t`)
        """
        test = node.test

        # Direct: if TYPE_CHECKING: or if TC: (when aliased via `from typing import TYPE_CHECKING as TC`)
        # Note: Only constant aliases are valid here, NOT module aliases.
        # `if t:` is NOT a TYPE_CHECKING guard even if `import typing as t` was used.
        if isinstance(test, ast.Name) and (
            test.id == "TYPE_CHECKING"
            or test.id in self._type_checking_constant_aliases
        ):
            return True

        # Attribute: if typing.TYPE_CHECKING: or if t.TYPE_CHECKING:
        if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
            # Check if it's typing.TYPE_CHECKING or an aliased version
            if isinstance(test.value, ast.Name):
                # typing.TYPE_CHECKING or aliased like t.TYPE_CHECKING
                # Note: Only module aliases are valid here for the prefix.
                if (
                    test.value.id == "typing"
                    or test.value.id in self._type_checking_module_aliases
                ):
                    return True
            return (
                False  # Only verified typing module references are TYPE_CHECKING guards
            )

        return False

    def visit_Import(self, node: ast.Import) -> None:
        """Handle `import X` and `import X as Y` statements."""
        # Track typing module aliases: import typing as t
        # These are only valid for attribute access: t.TYPE_CHECKING
        for alias in node.names:
            if alias.name == "typing" and alias.asname:
                self._type_checking_module_aliases.add(alias.asname)

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
        # These are valid as direct names: if TC:
        for alias in node.names:
            if alias.name == "TYPE_CHECKING":
                # If aliased, track the alias
                if alias.asname:
                    self._type_checking_constant_aliases.add(alias.asname)

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
    """Iterate over all Python files in a directory, skipping excluded paths.

    This function recursively traverses the given directory and yields paths to
    Python files (*.py), excluding files that match any of the skip directories
    or user-provided exclusion patterns.

    Args:
        root_dir: The root directory to start scanning from. Must be an existing
            directory path.
        excludes: A set of Path objects representing files or directories to exclude.
            Exclusions are matched using proper path component matching to avoid
            false positives from partial string matches.

    Yields:
        Path: Absolute paths to Python files that are not excluded.

    Exclusion Behavior:
        A file is excluded if any of the following conditions are met:
        1. The file is inside a directory listed in SKIP_DIRECTORIES (e.g., __pycache__)
        2. The file path is relative to any exclude_path (i.e., file is inside exclude_path)
        3. The exclude_path appears as a contiguous subsequence of path components
           (e.g., exclude="tests" matches "src/tests/file.py" but NOT "src/tests_util/file.py")
        4. The file's basename matches the exclude_path's basename exactly

    Thread Safety:
        This function is thread-safe as it only performs read-only filesystem operations
        and does not maintain any shared mutable state.

    Example:
        >>> excludes = {Path("tests"), Path("conftest.py")}
        >>> for py_file in iter_python_files(Path("src"), excludes):
        ...     print(py_file)
    """
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
                # path is not relative to exclude_path, use path component matching
                try:
                    # Check if exclude_path appears as a contiguous subsequence in path
                    # using PATH COMPONENT matching (not string matching).
                    #
                    # Why path components? This prevents partial string matches:
                    #   - path.parts gives tuples like ('src', 'tests', 'file.py')
                    #   - exclude "tests" (parts: ('tests',)) matches ('src', 'tests', 'file.py')
                    #   - exclude "tests" does NOT match ('src', 'tests_util', 'file.py')
                    #     because ('tests',) != ('tests_util',) as tuples
                    #
                    # Examples:
                    #   - Exclude "tests" MATCHES "src/tests/file.py"
                    #   - Exclude "tests" does NOT match "src/tests_util/file.py"
                    #   - Exclude "foo" does NOT match "foobar/file.py"
                    path_parts = path.parts
                    exclude_parts = exclude_path.parts
                    exclude_len = len(exclude_parts)
                    for i in range(len(path_parts) - exclude_len + 1):
                        if path_parts[i : i + exclude_len] == exclude_parts:
                            should_exclude = True
                            break
                    if should_exclude:
                        break
                    # Also check exact filename match (for single-file exclusions)
                    if exclude_path.name == path.name:
                        should_exclude = True
                        break
                except Exception:
                    # fallback-ok: skip exclusion check on path parsing errors
                    pass

        if not should_exclude:
            yield path


def check_file(
    file_path: Path,
) -> tuple[list[Violation], list[FileProcessingError]]:
    """Check a single Python file for banned transport imports.

    This function reads a Python file, parses it into an AST, and uses the
    TransportImportChecker visitor to detect any imports of banned transport/I/O
    modules that occur outside of TYPE_CHECKING blocks.

    Args:
        file_path: Absolute or relative path to the Python file to check.
            The file must be readable and contain valid Python syntax.

    Returns:
        A tuple of (violations, errors) where:
        - violations: List of Violation objects, each representing a banned import
          found at runtime scope (outside TYPE_CHECKING blocks). Empty list if no
          violations found.
        - errors: List of FileProcessingError objects representing non-fatal issues
          encountered during processing (e.g., permission denied, invalid syntax,
          encoding errors). These are warnings that do NOT cause the validator to
          fail (exit code 1). Empty list if no errors occurred.

    Error Handling:
        The function handles these error cases gracefully:
        - PermissionError: File cannot be read due to permissions
        - UnicodeDecodeError: File is not valid UTF-8 (possibly binary)
        - OSError: General file read failures
        - SyntaxError: File contains invalid Python syntax
        - Empty files are handled gracefully (no violations, no errors)

    Thread Safety:
        This function creates a new TransportImportChecker instance per call,
        making it safe to call from multiple threads concurrently.

    Example:
        >>> violations, errors = check_file(Path("src/module.py"))
        >>> if violations:
        ...     for v in violations:
        ...         print(f"{v.file_path}:{v.line_number}: {v.module_name}")
    """
    violations: list[Violation] = []
    errors: list[FileProcessingError] = []

    # Read file content with comprehensive error handling
    try:
        source_code = file_path.read_text(encoding="utf-8")
    except PermissionError as e:
        # boundary-ok: file system permission boundary - gracefully handle unreadable files
        errors.append(
            FileProcessingError(
                file_path=file_path,
                error_type="PermissionError",
                error_message=f"Cannot read file: {e}",
            )
        )
        return violations, errors
    except UnicodeDecodeError as e:
        # boundary-ok: encoding boundary - skip non-UTF-8 files (likely binary)
        errors.append(
            FileProcessingError(
                file_path=file_path,
                error_type="UnicodeDecodeError",
                error_message=f"File is not valid UTF-8 (possibly binary): {e}",
            )
        )
        return violations, errors
    except OSError as e:
        # boundary-ok: file system boundary - handle general I/O failures gracefully
        errors.append(
            FileProcessingError(
                file_path=file_path,
                error_type="OSError",
                error_message=f"Could not read file: {e}",
            )
        )
        return violations, errors

    # Handle empty files gracefully (valid Python, no imports to check)
    if not source_code.strip():
        return violations, errors

    # Parse the AST with error handling
    try:
        tree = ast.parse(source_code, filename=str(file_path))
    except SyntaxError as e:
        # boundary-ok: AST parsing boundary - skip files with invalid Python syntax
        errors.append(
            FileProcessingError(
                file_path=file_path,
                error_type="SyntaxError",
                error_message=f"Invalid Python syntax: {e.msg} (line {e.lineno})",
            )
        )
        return violations, errors

    checker = TransportImportChecker(source_code)
    checker.visit(tree)

    # Update file paths in violations
    for v in checker.violations:
        violations.append(
            Violation(
                file_path=file_path,
                line_number=v.line_number,
                module_name=v.module_name,
                import_statement=v.import_statement,
            )
        )

    return violations, errors


def main() -> int:
    """Main entry point for the transport import validator CLI.

    This function implements the command-line interface for the AST-based transport
    import validator. It scans Python files in the specified source directory and
    reports any banned transport/I/O library imports that occur outside of
    TYPE_CHECKING blocks.

    CLI Arguments:
        --src-dir PATH: Source directory to scan (default: src/omnibase_core)
        --exclude PATH: Exclude a file or directory (can be specified multiple times)
        --verbose, -v: Show import statement snippets for each violation

    Returns:
        int: Exit code indicating the validation result:
            - 0: Success - no violations found (file processing errors are warnings only)
            - 1: Failure - one or more violations found, OR source directory is invalid

    Output:
        - Violations are printed to stdout with file path, line number, and module name
        - File processing errors (non-fatal warnings) are printed to stderr
        - Summary statistics are always printed at the end

    Exit Code Semantics:
        The exit code is determined ONLY by violations, not by file processing errors.
        This means:
        - Files that cannot be read (permissions, encoding) cause warnings but NOT failure
        - Files with syntax errors cause warnings but NOT failure
        - Only actual banned imports cause exit code 1

    Example Usage:
        # Basic validation
        uv run python scripts/validate_no_transport_imports.py

        # Verbose output with import snippets
        uv run python scripts/validate_no_transport_imports.py --verbose

        # Exclude specific paths
        uv run python scripts/validate_no_transport_imports.py --exclude tests/

        # Scan different directory
        uv run python scripts/validate_no_transport_imports.py --src-dir src/other
    """
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

    # Collect all violations and errors
    excludes = set(args.excludes)
    all_violations: list[Violation] = []
    all_errors: list[FileProcessingError] = []
    file_count = 0

    print(f"Checking for transport/I/O library imports in {src_dir}...")

    for file_path in iter_python_files(src_dir, excludes):
        file_count += 1
        violations, errors = check_file(file_path)
        all_violations.extend(violations)
        all_errors.extend(errors)

    # Report errors to stderr (these are warnings, not failures)
    if all_errors:
        print("\nWarnings (file processing errors):", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        print(file=sys.stderr)

    # Report violations to stdout
    if all_violations:
        print("\nERROR: Found transport/I/O library imports in omnibase_core!")
        print()
        print("Violations:")
        for v in all_violations:
            print(f"  {v}")
            if args.verbose:
                print(f"    -> {v.import_statement}")
        print()
        print(
            "Architectural Invariant: omnibase_core must be pure (no I/O dependencies)."
        )
        print("Transport and I/O libraries belong in infrastructure layers.")
        print()
        print("Solutions:")
        print("  1. Define a protocol in omnibase_core for the capability you need")
        print("  2. Implement the protocol in an infrastructure package")
        print(
            "  3. Use TYPE_CHECKING guards for type-only imports (allowed per ADR-005)"
        )
        print()
        print(
            f"Total: {len(all_violations)} violation(s), "
            f"{len(all_errors)} error(s) in {file_count} files scanned"
        )
        return 1

    # Success case - still report error count if any
    if all_errors:
        print(
            f"No transport/I/O library imports found in omnibase_core "
            f"({file_count} files scanned, {len(all_errors)} file(s) could not be processed)"
        )
    else:
        print(
            f"No transport/I/O library imports found in omnibase_core "
            f"({file_count} files scanned)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
