#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Bare model_dump() Detection

Detects bare model_dump() calls that lack mode="json", which can produce
non-JSON-safe types (tuples, sets, UUIDs, datetimes) at serialization
boundaries, leading to TypeError or data corruption.

ANTI-PATTERNS DETECTED:
  .model_dump()              — no mode= keyword argument
  .model_dump(exclude=...)   — has other kwargs but no mode=

ACCEPTABLE PATTERNS:
  .model_dump(mode="json")               — explicit JSON-safe output
  .model_dump(mode="json", exclude=...)   — with other kwargs
  .model_dump()  # noqa: model-dump-bare  — intentional suppression

SUPPRESSION STANDARD:
  # noqa: model-dump-bare is allowed only for in-memory dict-to-dict usage
  that does not cross JSON, hashing, persistence, transport, or validation
  boundaries. Suppressions are exception markers, not convenience tools.
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Any


class ModelDumpModeDetector(ast.NodeVisitor):
    """AST visitor to detect bare model_dump() calls without mode= argument."""

    def __init__(self, source_lines: list[str]) -> None:
        self.violations: list[dict[str, Any]] = []
        self.current_file = ""
        self.source_lines = source_lines

    def visit_Call(self, node: ast.Call) -> None:
        """Check for model_dump() calls without mode= keyword argument."""
        if isinstance(node.func, ast.Attribute) and node.func.attr == "model_dump":
            # Check if mode= is present in keyword arguments
            has_mode = any(kw.arg == "mode" for kw in node.keywords)

            if not has_mode:
                # Check for noqa suppression on the same line
                line_idx = node.lineno - 1
                if line_idx < len(self.source_lines):
                    line_text = self.source_lines[line_idx]
                    if "# noqa: model-dump-bare" in line_text:
                        # Suppressed — skip this violation
                        self.generic_visit(node)
                        return

                self.violations.append(
                    {
                        "file": self.current_file,
                        "line": node.lineno,
                        "type": "bare_model_dump",
                        "message": (
                            "Bare model_dump() without mode=\"json\" — "
                            "may produce non-JSON-safe types (tuples, sets, UUIDs). "
                            "Fix: model_dump() -> model_dump(mode=\"json\")"
                        ),
                    }
                )

        self.generic_visit(node)

    def check_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Check a single Python file for bare model_dump() calls."""
        self.current_file = str(file_path)
        self.violations = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            self.source_lines = content.splitlines()

            # Parse and visit the AST
            tree = ast.parse(content)
            self.visit(tree)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(
                f"Warning: Skipping unparsable file {file_path}: {e}",
                file=sys.stderr,
            )
        except (OSError, ValueError) as e:
            print(f"Warning: Could not process {file_path}: {e}", file=sys.stderr)

        return self.violations


def find_python_files(directory: Path, exclude_patterns: list[str]) -> list[Path]:
    """Find all Python files, excluding specified patterns.

    Returns files in deterministic order for stable CI output.
    """
    python_files = []

    for py_file in directory.rglob("*.py"):
        # Check if file matches any exclude pattern (use POSIX paths for
        # cross-platform consistency — forward slashes on all OSes)
        file_str = py_file.as_posix()
        should_exclude = any(pattern in file_str for pattern in exclude_patterns)

        if not should_exclude:
            python_files.append(py_file)

    # Sort files by path for deterministic order across different systems
    python_files.sort(key=lambda p: str(p))
    return python_files


def main() -> int:
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Detect bare model_dump() calls without mode='json'"
    )
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0)",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default="src/",
        help="Directory to scan (default: src/)",
    )

    args = parser.parse_args()

    if args.max_violations < 0:
        parser.error("--max-violations must be >= 0")

    # Define exclude patterns
    exclude_patterns = [
        "tests/",
        "archive/",
        "archived/",
        "__pycache__/",
        ".git/",
        "scripts/validation/",  # Don't scan validation scripts themselves
    ]

    base_dir = Path(args.directory)
    if not base_dir.exists():
        print(f"Directory {base_dir} does not exist")
        return 1

    # Find Python files
    python_files = find_python_files(base_dir, exclude_patterns)

    if not python_files:
        print("No Python files found to check")
        return 0

    # Check each file
    all_violations: list[dict[str, Any]] = []

    for py_file in python_files:
        detector = ModelDumpModeDetector([])
        violations = detector.check_file(py_file)
        all_violations.extend(violations)

    # Report results
    violation_count = len(all_violations)

    if violation_count == 0:
        print("No bare model_dump() violations detected")
        return 0

    print(f"Found {violation_count} bare model_dump() violation(s):")
    print()

    # Group violations by file
    violations_by_file: dict[str, list[dict[str, Any]]] = {}
    for violation in all_violations:
        file_path = violation["file"]
        if file_path not in violations_by_file:
            violations_by_file[file_path] = []
        violations_by_file[file_path].append(violation)

    # Sort violations by file path and then by line number for reproducible output
    for file_path in list(violations_by_file.keys()):
        violations_by_file[file_path].sort(key=lambda v: v["line"])

    # Print violations grouped by file in deterministic order
    for file_path in sorted(violations_by_file.keys()):
        violations = violations_by_file[file_path]
        # Use relative path for cleaner output when possible
        try:
            relative_path = Path(file_path).relative_to(Path.cwd())
            display_path = str(relative_path)
        except ValueError:
            # If relative path computation fails, use absolute path
            display_path = file_path

        print(f"  {display_path}")
        for violation in violations:
            print(f"    Line {violation['line']}: {violation['message']}")
        print()

    print("FIX: model_dump() -> model_dump(mode=\"json\")")
    print(
        "SUPPRESS: Add '# noqa: model-dump-bare' for intentional in-memory dict-to-dict usage"
    )

    # Check against limit
    if violation_count > args.max_violations:
        print()
        print(
            f"Violation count ({violation_count}) exceeds maximum allowed ({args.max_violations})"
        )
        return 1

    print()
    print(
        f"Violation count ({violation_count}) is within maximum allowed ({args.max_violations})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
