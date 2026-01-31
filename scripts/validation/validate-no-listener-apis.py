#!/usr/bin/env python3
"""
ONEX Listener API Prevention Validation.

OMN-1747: Listener/consumer lifecycle management was removed from omnibase_core.
This pre-commit hook prevents these APIs from being reintroduced.

For Kafka consumer management, use EventBusSubcontractWiring in omnibase_infra.

Detected Patterns:
1. def start_event_listener( - Listener start method
2. def stop_event_listener( - Listener stop method
3. def _event_listener_loop( - Internal listener loop
4. class ModelEventBusListenerHandle - Listener handle model
5. from ... import ... ModelEventBusListenerHandle - Imports of listener handle

Usage:
    # Check specific files (pre-commit mode)
    poetry run python scripts/validation/validate-no-listener-apis.py <file1> [file2] ...

    # Check entire src/ directory (default)
    poetry run python scripts/validation/validate-no-listener-apis.py

    # Check specific directory
    poetry run python scripts/validation/validate-no-listener-apis.py src/omnibase_core/

    To allow listener APIs in specific files (rare cases), add comment:
    # listener-api-ok: reason for exception

Rationale:
    - omnibase_core must remain transport-agnostic (ADR-005)
    - Listener lifecycle creates tight coupling to Kafka implementation
    - Consumer management belongs in omnibase_infra via EventBusSubcontractWiring
    - Core should only define protocols, not implementations

Reference:
    - OMN-1747: Remove listener management from omnibase_core
    - docs/architecture/adr/ADR-005-core-infra-dependency-boundary.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Number of lines to check for bypass comment (check entire file for patterns)
BYPASS_CHECK_LINES = 20

# Forbidden listener API patterns with explanations
# Order matters: more specific patterns should come first to avoid duplicate detection
FORBIDDEN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
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
    (
        # Matches both "from x import ModelEventBusListenerHandle" and
        # "import x.ModelEventBusListenerHandle" style imports
        re.compile(r"\b(?:from\s+\S+\s+)?import\s+.*\bModelEventBusListenerHandle\b"),
        "ModelEventBusListenerHandle import forbidden - listener handles not needed in core",
    ),
]

# Bypass comment pattern
BYPASS_PATTERN = re.compile(r"#\s*listener-api-ok:", re.IGNORECASE)


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a Python file for forbidden listener API patterns.

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

    # Check each line for forbidden patterns
    for line_num, line in enumerate(lines, start=1):
        # Skip comment lines (patterns in comments are informational)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue

        for pattern, message in FORBIDDEN_PATTERNS:
            if pattern.search(line):
                violations.append((line_num, message, line.rstrip()))

    return violations


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Prevent listener management APIs from being introduced to omnibase_core"
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
        print("ONEX Listener API Prevention Failed")  # print-ok: CLI output
        print(f"{'=' * 70}\n")  # print-ok: CLI output

        print(  # print-ok: CLI output
            f"Found {len(all_violations)} forbidden listener API(s):\n"
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
        print("\nWhy listener APIs are not allowed in omnibase_core:")  # print-ok: CLI output
        print(  # print-ok: CLI output
            "  - OMN-1747: Listener lifecycle removed from core (transport-agnostic)"
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
            "  1. Remove the listener API code from omnibase_core"
        )
        print(  # print-ok: CLI output
            "  2. If needed, implement in omnibase_infra instead"
        )
        print(  # print-ok: CLI output
            "\nFor rare legitimate exceptions, add this comment in the first 20 lines:"
        )
        print("  # listener-api-ok: <reason for exception>")  # print-ok: CLI output

        return 1

    if args.verbose:
        print(  # print-ok: CLI output
            f"Checked {len(files_to_check)} files - no forbidden listener APIs found"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
