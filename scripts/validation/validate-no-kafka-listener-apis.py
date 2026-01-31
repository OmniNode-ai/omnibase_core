#!/usr/bin/env python3
"""
ONEX Listener API and Kafka Client Import Prevention Validation.

OMN-1747: Listener/consumer lifecycle management was removed from omnibase_core.
OMN-1745: Direct Kafka client imports are forbidden in omnibase_core.
This pre-commit hook prevents these APIs from being reintroduced.

For Kafka consumer management, use EventBusSubcontractWiring in omnibase_infra.

Detected Patterns:
1. def start_event_listener( - Listener start method
2. def stop_event_listener( - Listener stop method
3. def _event_listener_loop( - Internal listener loop
4. class ModelEventBusListenerHandle - Listener handle model
5. from ... import ... ModelEventBusListenerHandle - Imports of listener handle
6. from ... import ... AIOKafkaConsumer - Direct async Kafka consumer import
7. from ... import ... KafkaConsumer - Direct sync Kafka consumer import
8. from ... import ... AIOKafkaProducer - Direct async Kafka producer import
9. from ... import ... KafkaProducer - Direct sync Kafka producer import

Usage:
    # Check specific files (pre-commit mode)
    poetry run python scripts/validation/validate-no-kafka-listener-apis.py <file1> [file2] ...

    # Check entire src/ directory (default)
    poetry run python scripts/validation/validate-no-kafka-listener-apis.py

    # Check specific directory
    poetry run python scripts/validation/validate-no-kafka-listener-apis.py src/omnibase_core/

    To allow listener APIs or Kafka imports in specific files (rare cases), add comment:
    # listener-api-ok: reason for exception
    # kafka-import-ok: reason for exception

Rationale:
    - omnibase_core must remain transport-agnostic (ADR-005)
    - Listener lifecycle creates tight coupling to Kafka implementation
    - Direct Kafka consumer imports bypass the transport abstraction layer
    - Consumer management belongs in omnibase_infra via EventBusSubcontractWiring
    - Core should only define protocols, not implementations

Reference:
    - OMN-1745: Block direct Kafka consumer imports in omnibase_core
    - OMN-1747: Remove listener management from omnibase_core
    - docs/architecture/adr/ADR-005-core-infra-dependency-boundary.md
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# Number of lines to check for bypass comment (check entire file for patterns)
BYPASS_CHECK_LINES = 20

# Forbidden listener API patterns (non-import) - checked via regex
# These are function/class definitions that indicate listener management code
FORBIDDEN_DEFINITION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bdef\s+start_event_listener\s*\("),
        "start_event_listener() removed - use EventBusSubcontractWiring in infra",
    ),
    (
        re.compile(r"\bdef\s+stop_event_listener\s*\("),
        "stop_event_listener() removed - use EventBusSubcontractWiring in infra",
    ),
    (
        re.compile(r"\bdef\s+_event_listener_loop\s*\("),
        "_event_listener_loop() removed - use EventBusSubcontractWiring in infra",
    ),
    (
        re.compile(r"\bclass\s+ModelEventBusListenerHandle\b"),
        "ModelEventBusListenerHandle removed - listener handles not needed in core",
    ),
]

# Forbidden import names - checked via AST parsing
# AST parsing catches multiline imports that regex misses:
#   from kafka import (
#       KafkaConsumer,  # This line alone lacks "import" keyword
#   )
FORBIDDEN_IMPORT_NAMES: dict[str, str] = {
    "AIOKafkaConsumer": (
        "Direct AIOKafkaConsumer import forbidden - use EventBusSubcontractWiring in infra"
    ),
    "KafkaConsumer": (
        "Direct KafkaConsumer import forbidden - use EventBusSubcontractWiring in infra"
    ),
    "AIOKafkaProducer": (
        "Direct AIOKafkaProducer import forbidden - use EventBusSubcontractWiring in infra"
    ),
    "KafkaProducer": (
        "Direct KafkaProducer import forbidden - use EventBusSubcontractWiring in infra"
    ),
    "ModelEventBusListenerHandle": (
        "ModelEventBusListenerHandle import forbidden - listener handles not needed in core"
    ),
}

# Bypass comment patterns - accepts either listener-api-ok or kafka-import-ok
BYPASS_PATTERN = re.compile(r"#\s*(?:listener-api-ok|kafka-import-ok):", re.IGNORECASE)


def check_file_ast_imports(
    filepath: Path, content: str, lines: list[str]
) -> list[tuple[int, str, str]]:
    """
    Check for forbidden imports using AST parsing.

    AST parsing catches multiline imports that regex-based scanning misses:
        from kafka import (
            KafkaConsumer,  # This line lacks "import" keyword
        )

    Args:
        filepath: Path to the Python file (for error context)
        content: Full file content as string
        lines: List of lines for extracting violation content

    Returns:
        List of (line_number, violation_message, line_content) tuples
    """
    violations: list[tuple[int, str, str]] = []

    try:
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError:
        # File has syntax errors - skip AST analysis
        # Other tools (mypy, pyright) will report syntax errors
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # Handle "import kafka.KafkaConsumer" or "import KafkaConsumer"
            for alias in node.names:
                # Check both full path and final component
                # e.g., "kafka.KafkaConsumer" -> check "KafkaConsumer"
                name_parts = alias.name.split(".")
                for part in name_parts:
                    if part in FORBIDDEN_IMPORT_NAMES:
                        line_content = (
                            lines[node.lineno - 1].rstrip()
                            if node.lineno <= len(lines)
                            else f"import {alias.name}"
                        )
                        violations.append(
                            (node.lineno, FORBIDDEN_IMPORT_NAMES[part], line_content)
                        )
                        break  # Only report once per alias

        elif isinstance(node, ast.ImportFrom):
            # Handle "from kafka import KafkaConsumer" (including multiline)
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORT_NAMES:
                    line_content = (
                        lines[node.lineno - 1].rstrip()
                        if node.lineno <= len(lines)
                        else f"from {node.module} import {alias.name}"
                    )
                    violations.append(
                        (
                            node.lineno,
                            FORBIDDEN_IMPORT_NAMES[alias.name],
                            line_content,
                        )
                    )

    return violations


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a Python file for forbidden listener API and Kafka client patterns.

    Uses two detection methods:
    1. AST parsing for imports - catches multiline imports that regex misses
    2. Regex for non-import patterns (function/class definitions)

    Args:
        filepath: Path to the Python file to check

    Returns:
        List of (line_number, violation_type, line_content) tuples for violations
    """
    violations: list[tuple[int, str, str]] = []

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()
    except (OSError, UnicodeDecodeError) as e:
        # Skip files that can't be read (will be caught by other tools)
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return violations

    # Check for bypass comment in the header
    for i, line in enumerate(lines[:BYPASS_CHECK_LINES]):
        if BYPASS_PATTERN.search(line):
            return violations  # File has explicit bypass

    # Check for forbidden imports using AST (catches multiline imports)
    ast_violations = check_file_ast_imports(filepath, content, lines)
    violations.extend(ast_violations)

    # Check each line for forbidden definition patterns (def/class)
    for line_num, line in enumerate(lines, start=1):
        # Skip comment lines (patterns in comments are informational)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        for pattern, message in FORBIDDEN_DEFINITION_PATTERNS:
            if pattern.search(line):
                violations.append((line_num, message, line.rstrip()))

    return violations


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Prevent listener APIs and direct Kafka client imports in omnibase_core"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to check (defaults to src/omnibase_core/ if none provided)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Default to src/omnibase_core/ if no paths provided
    paths = args.paths if args.paths else [Path("src/omnibase_core/")]

    # Collect all Python files to check
    files_to_check: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files_to_check.append(path)
        elif path.is_dir():
            files_to_check.extend(path.rglob("*.py"))
        elif not path.exists():
            print(f"Warning: Path does not exist: {path}", file=sys.stderr)

    if not files_to_check:
        if args.verbose:
            print("No Python files found to check")  # print-ok: CLI output
        return 0

    all_violations: list[tuple[Path, int, str, str]] = []

    for filepath in sorted(files_to_check):
        violations = check_file(filepath)
        for line_num, violation_type, line_content in violations:
            all_violations.append((filepath, line_num, violation_type, line_content))

    if all_violations:
        print(f"\n{'=' * 70}")  # print-ok: CLI output
        print("ONEX Listener API / Kafka Client Import Prevention Failed")  # print-ok: CLI output
        print(f"{'=' * 70}\n")  # print-ok: CLI output

        print(  # print-ok: CLI output
            f"Found {len(all_violations)} forbidden pattern(s):\n"
        )

        for filepath, line_num, violation_type, line_content in all_violations:
            print(f"  {filepath}:{line_num}")  # print-ok: CLI output
            print(f"    Violation: {violation_type}")  # print-ok: CLI output
            truncated = (
                line_content[:70] + "..."
                if len(line_content) > 70
                else line_content
            )
            print(f"    Content: {truncated}")  # print-ok: CLI output
            print()  # print-ok: CLI output

        print("-" * 70)  # print-ok: CLI output
        print("\nWhy these patterns are not allowed in omnibase_core:")  # print-ok: CLI output
        print(  # print-ok: CLI output
            "  - OMN-1747: Listener lifecycle removed from core (transport-agnostic)"
        )
        print(  # print-ok: CLI output
            "  - OMN-1745: Direct Kafka client imports bypass transport abstraction"
        )
        print(  # print-ok: CLI output
            "  - Core should only define protocols, not Kafka implementations"
        )
        print(  # print-ok: CLI output
            "  - Use EventBusSubcontractWiring in omnibase_infra for consumers"
        )
        print(  # print-ok: CLI output
            "  - See ADR-005 for core/infra dependency boundary"
        )
        print("\nTo fix:")  # print-ok: CLI output
        print(  # print-ok: CLI output
            "  1. Remove the listener API or Kafka client import from omnibase_core"
        )
        print(  # print-ok: CLI output
            "  2. If needed, implement in omnibase_infra instead"
        )
        print(  # print-ok: CLI output
            "\nFor rare legitimate exceptions, add this comment in the first 20 lines:"
        )
        print("  # listener-api-ok: <reason for exception>")  # print-ok: CLI output
        print("  # kafka-import-ok: <reason for exception>")  # print-ok: CLI output

        return 1

    if args.verbose:
        print(  # print-ok: CLI output
            f"Checked {len(files_to_check)} files - no forbidden listener/Kafka client patterns found"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
