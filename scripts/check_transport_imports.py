#!/usr/bin/env python3
"""
ONEX Transport Import Validation.

AST-based import scanning to ensure omnibase_core does not contain direct
imports of transport/infrastructure libraries. These libraries belong in
omnibase_spi or service layers, not in the core framework.

This enforces the ONEX architecture principle of dependency inversion:
omnibase_core provides abstractions (protocols), while omnibase_spi
provides concrete implementations using transport libraries.

FORBIDDEN IMPORTS:
- kafka, aiokafka: Message queue clients (use ProtocolEventBus)
- httpx, aiohttp, requests: HTTP clients (use ProtocolHttpClient)
- asyncpg, psycopg, psycopg2: Database clients (use ProtocolRepository)
- hvac: HashiCorp Vault client (use ProtocolSecretStore)
- consul: Service discovery client (use ProtocolServiceDiscovery)
- redis, valkey: Cache/queue clients (use ProtocolCache)

ALLOWED PATTERNS:
- Protocol definitions that abstract these transports
- Type stubs for type checking (if __TYPE_CHECKING__)
- Test mocks and fixtures

Usage:
    poetry run python scripts/check_transport_imports.py
    poetry run python scripts/check_transport_imports.py --verbose
    poetry run python scripts/check_transport_imports.py --json
    poetry run python scripts/check_transport_imports.py --file src/omnibase_core/some_file.py

Exit Codes:
    0 - No transport import violations found
    1 - Transport import violations detected (blocks PR)
    2 - Script error (invalid arguments, file not found, etc.)

Related:
    - Linear Ticket: OMN-220
    - Architecture: docs/architecture/DEPENDENCY_INVERSION.md
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import NamedTuple


class ViolationType(Enum):
    """Types of transport import violations."""

    BANNED_TRANSPORT_IMPORT = "banned_transport_import"
    SYNTAX_ERROR = "syntax_error"


class Severity(Enum):
    """Severity levels for violations."""

    ERROR = "error"  # Blocks CI


@dataclass
class TransportViolation:
    """A single transport import violation found in a source file."""

    file_path: Path
    line_number: int
    column: int
    violation_type: ViolationType
    severity: Severity
    message: str
    suggestion: str
    code_snippet: str = ""

    def format(self, verbose: bool = False) -> str:
        """Format violation for output.

        Args:
            verbose: If True, include code snippet in output.

        Returns:
            Formatted violation string for display.
        """
        location = f"{self.file_path}:{self.line_number}:{self.column}"
        level = "ERROR" if self.severity == Severity.ERROR else "WARNING"

        result = f"[{level}] {location}\n"
        result += f"  {self.violation_type.value}: {self.message}\n"
        result += f"  Suggestion: {self.suggestion}\n"

        if verbose and self.code_snippet:
            result += f"  Code: {self.code_snippet}\n"

        return result


class TransportCheckResult(NamedTuple):
    """Result of transport import check for a single file."""

    file_path: Path
    violations: list[TransportViolation]
    is_clean: bool
    skip_reason: str | None


# ==============================================================================
# BANNED TRANSPORT MODULES CONFIGURATION
# ==============================================================================

# Transport libraries that are FORBIDDEN in omnibase_core
# These should only be used in omnibase_spi or service layers
BANNED_TRANSPORT_MODULES: frozenset[str] = frozenset(
    {
        # Message queue clients
        "kafka",
        "aiokafka",
        # HTTP clients
        "httpx",
        "aiohttp",
        "requests",
        # Database clients
        "asyncpg",
        "psycopg",
        "psycopg2",
        # Secret store clients
        "hvac",
        # Service discovery clients
        "consul",
        # Cache/queue clients
        "redis",
        "valkey",
    }
)

# Protocol alternatives for banned transports
TRANSPORT_ALTERNATIVES: dict[str, str] = {
    "kafka": "ProtocolEventBus",
    "aiokafka": "ProtocolEventBus",
    "httpx": "ProtocolHttpClient",
    "aiohttp": "ProtocolHttpClient",
    "requests": "ProtocolHttpClient",
    "asyncpg": "ProtocolRepository",
    "psycopg": "ProtocolRepository",
    "psycopg2": "ProtocolRepository",
    "hvac": "ProtocolSecretStore",
    "consul": "ProtocolServiceDiscovery",
    "redis": "ProtocolCache",
    "valkey": "ProtocolCache",
}

# Temporary allowlist for pre-existing violations
# These should be fixed and removed from this list
# Each entry is a relative path from src/omnibase_core/
#
# EXPIRATION: Review and remove allowlisted items by 2025-03-01
# TODO: Create separate tickets to fix these and remove from allowlist
TEMPORARY_ALLOWLIST: frozenset[str] = frozenset(
    {
        # TODO: Create ticket - mixin_health_check.py uses aiohttp directly for HTTP
        # health checks. Should use ProtocolHttpClient instead.
        "mixins/mixin_health_check.py",
    }
)


# ==============================================================================
# AST VISITOR
# ==============================================================================


@dataclass
class TransportImportAnalyzer(ast.NodeVisitor):
    """AST visitor to detect banned transport library imports.

    Scans the AST for import statements that reference banned transport
    libraries. These libraries should not be imported directly in
    omnibase_core - instead, protocols should be used for abstraction.

    Attributes:
        file_path: Path to the file being analyzed.
        source_lines: List of source code lines for snippet extraction.
        violations: List of detected transport import violations.
        in_type_checking_block: Whether currently inside TYPE_CHECKING block.
    """

    file_path: Path
    source_lines: list[str]
    violations: list[TransportViolation] = field(default_factory=list)
    in_type_checking_block: bool = False

    def visit_If(self, node: ast.If) -> None:
        """Track TYPE_CHECKING blocks to allow type-only imports.

        Args:
            node: AST if statement node to analyze.
        """
        # Check if this is a TYPE_CHECKING block
        if self._is_type_checking_condition(node.test):
            # Save state and mark as in type checking block
            prev_state = self.in_type_checking_block
            self.in_type_checking_block = True
            # Visit the body of the if block
            for child in node.body:
                self.visit(child)
            # Restore state
            self.in_type_checking_block = prev_state
            # Visit else/elif parts normally
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements for banned transport modules.

        Detects `import X` and `import X as Y` patterns.

        Args:
            node: AST import node to check.
        """
        if self.in_type_checking_block:
            # Allow type-only imports inside TYPE_CHECKING blocks
            return

        for alias in node.names:
            module_name = alias.name
            self._check_banned_module(node, module_name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check 'from ... import ...' statements for banned transport modules.

        Detects `from X import Y` patterns.

        Args:
            node: AST import-from node to check.
        """
        if self.in_type_checking_block:
            # Allow type-only imports inside TYPE_CHECKING blocks
            return

        module_name = node.module or ""
        self._check_banned_module(node, module_name)

    def _is_type_checking_condition(self, test: ast.expr) -> bool:
        """Check if condition is TYPE_CHECKING or typing.TYPE_CHECKING.

        Args:
            test: AST expression to check.

        Returns:
            True if this is a TYPE_CHECKING condition.
        """
        # Check for `if TYPE_CHECKING:`
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        # Check for `if typing.TYPE_CHECKING:`
        if isinstance(test, ast.Attribute):
            if test.attr == "TYPE_CHECKING":
                if isinstance(test.value, ast.Name) and test.value.id == "typing":
                    return True
        return False

    def _check_banned_module(self, node: ast.AST, module_name: str) -> None:
        """Check if a module import is banned in omnibase_core.

        Args:
            node: AST node for error location reporting.
            module_name: Fully qualified module name to check.
        """
        # Get the root module (e.g., "kafka" from "kafka.producer")
        root_module = module_name.split(".")[0]

        if root_module in BANNED_TRANSPORT_MODULES:
            alternative = TRANSPORT_ALTERNATIVES.get(
                root_module, "protocol abstraction"
            )
            self._add_violation(
                node,
                ViolationType.BANNED_TRANSPORT_IMPORT,
                Severity.ERROR,
                f"Import of '{module_name}' is forbidden in omnibase_core",
                f"Transport libraries belong in omnibase_spi or service layers. "
                f"Use {alternative} instead.",
            )

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
            violation_type: Type of transport import violation.
            severity: Severity level (ERROR).
            message: Human-readable description of the violation.
            suggestion: Suggested fix for the violation.
        """
        line_number = getattr(node, "lineno", 0)
        column = getattr(node, "col_offset", 0)

        # Get code snippet
        code_snippet = ""
        if 0 < line_number <= len(self.source_lines):
            code_snippet = self.source_lines[line_number - 1].strip()

        self.violations.append(
            TransportViolation(
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


def analyze_file(file_path: Path) -> TransportCheckResult:
    """Analyze a single file for banned transport imports.

    Parses the file as an AST and scans for import statements that
    reference banned transport libraries.

    Args:
        file_path: Path to the Python file to analyze.

    Returns:
        TransportCheckResult with violations and analysis status.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
        source_lines = source.splitlines()
        tree = ast.parse(source, filename=str(file_path))

        # Analyze for transport import violations
        analyzer = TransportImportAnalyzer(
            file_path=file_path,
            source_lines=source_lines,
        )
        analyzer.visit(tree)

        return TransportCheckResult(
            file_path=file_path,
            violations=analyzer.violations,
            is_clean=len(analyzer.violations) == 0,
            skip_reason=None,
        )

    except SyntaxError as e:
        return TransportCheckResult(
            file_path=file_path,
            violations=[
                TransportViolation(
                    file_path=file_path,
                    line_number=e.lineno or 0,
                    column=e.offset or 0,
                    violation_type=ViolationType.SYNTAX_ERROR,
                    severity=Severity.ERROR,
                    message=f"Syntax error: {e.msg}",
                    suggestion="Fix the syntax error before transport check can run",
                )
            ],
            is_clean=False,
            skip_reason=f"Syntax error: {e.msg}",
        )
    except Exception as e:
        return TransportCheckResult(
            file_path=file_path,
            violations=[],
            is_clean=False,
            skip_reason=f"Error analyzing file: {e}",
        )


def find_python_files(src_dir: Path) -> list[Path]:
    """Find all Python files in the source directory.

    Recursively searches for .py files, excluding __pycache__ directories.

    Args:
        src_dir: Source directory to search (typically src/omnibase_core).

    Returns:
        Sorted list of paths to Python files.
    """
    python_files: list[Path] = []

    for py_file in src_dir.rglob("*.py"):
        # Skip __pycache__ directories
        if "__pycache__" in py_file.parts:
            continue
        python_files.append(py_file)

    return sorted(python_files)


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


def _is_allowlisted(file_path: Path, src_dir: Path) -> bool:
    """Check if a file is in the temporary allowlist.

    Args:
        file_path: Absolute path to the file.
        src_dir: The src/omnibase_core directory.

    Returns:
        True if file is allowlisted and violations should be suppressed.
    """
    try:
        relative_path = str(file_path.relative_to(src_dir))
        return relative_path in TEMPORARY_ALLOWLIST
    except ValueError:
        return False


def main() -> int:
    """Main entry point for the transport import validation script.

    Parses command line arguments, finds Python files, runs transport
    import analysis, and reports results.

    Returns:
        Exit code:
        - 0: No transport import violations found
        - 1: Transport import violations detected
        - 2: Script error (invalid arguments, file not found, etc.)
    """
    parser = argparse.ArgumentParser(
        description="Validate omnibase_core does not import transport libraries directly"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with code snippets",
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        help="Check a specific file instead of all Python files",
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
        help="Output results as JSON for machine processing",
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
        error_msg = f"Error: Source directory not found: {src_dir}"
        if args.json:
            print(json.dumps({"error": error_msg}))
        else:
            print(error_msg, file=sys.stderr)
        return 2

    # Find files to analyze
    if args.file:
        if not args.file.exists():
            error_msg = f"Error: File not found: {args.file}"
            if args.json:
                print(json.dumps({"error": error_msg}))
            else:
                print(error_msg, file=sys.stderr)
            return 2
        python_files = [args.file]
    else:
        python_files = find_python_files(src_dir)

    if not python_files:
        if args.json:
            print(
                json.dumps(
                    {
                        "summary": {
                            "total_files": 0,
                            "clean_files": 0,
                            "files_with_violations": 0,
                            "total_violations": 0,
                        },
                        "results": [],
                    }
                )
            )
        else:
            print("No Python files found to analyze")
        return 0

    if args.verbose and not args.json:
        print(f"Analyzing {len(python_files)} Python files in {src_dir}")
        print()

    # Analyze each file
    results: list[TransportCheckResult] = []
    allowlisted_violations: list[TransportCheckResult] = []
    for file_path in python_files:
        result = analyze_file(file_path)
        # Check if file is allowlisted (suppress violations for pre-existing issues)
        if result.violations and _is_allowlisted(file_path, src_dir):
            allowlisted_violations.append(result)
            # Mark as clean since it's allowlisted
            result = TransportCheckResult(
                file_path=result.file_path,
                violations=[],
                is_clean=True,
                skip_reason="Allowlisted (pre-existing violation, see TEMPORARY_ALLOWLIST)",
            )
        results.append(result)

    # Calculate summary statistics
    total_files = len(results)
    clean_files = sum(1 for r in results if r.is_clean)
    files_with_violations = sum(1 for r in results if not r.is_clean)
    total_violations = sum(len(r.violations) for r in results)
    allowlisted_count = len(allowlisted_violations)

    # Output results
    if args.json:
        output = {
            "summary": {
                "total_files": total_files,
                "clean_files": clean_files,
                "files_with_violations": files_with_violations,
                "total_violations": total_violations,
                "allowlisted_files": allowlisted_count,
            },
            "results": [
                {
                    "file": str(r.file_path),
                    "is_clean": r.is_clean,
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
                if r.violations or r.skip_reason
            ],
        }
        print(json.dumps(output, indent=2))
        return 0 if files_with_violations == 0 else 1

    # Text output
    for result in results:
        if result.skip_reason and args.verbose:
            relative_path = _safe_relative_path(result.file_path, src_dir.parent.parent)
            print(f"SKIP: {relative_path} - {result.skip_reason}")
            continue

        if result.violations:
            for violation in result.violations:
                print(violation.format(args.verbose))

    # Summary
    print()
    print("=" * 60)
    print("Transport Import Check Summary")
    print("=" * 60)
    print(f"  Total files scanned: {total_files}")
    print(f"  Clean files: {clean_files}")
    print(f"  Files with violations: {files_with_violations}")
    print(f"  Total violations: {total_violations}")
    if allowlisted_count > 0:
        print(
            f"  Allowlisted files: {allowlisted_count} (pre-existing, tracked for fix)"
        )

    if files_with_violations > 0:
        print()
        print("FAILED: Transport import violations detected")
        print()
        print("Transport libraries should not be imported directly in omnibase_core.")
        print(
            "These belong in omnibase_spi or service layers that implement protocols."
        )
        print()
        print("Protocol alternatives:")
        for transport, protocol in sorted(TRANSPORT_ALTERNATIVES.items()):
            print(f"  - {transport} -> {protocol}")
        return 1

    print()
    print("PASSED: No transport import violations found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
