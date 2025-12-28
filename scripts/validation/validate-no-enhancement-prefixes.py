#!/usr/bin/env python3
"""
ONEX Enhancement Prefix Detection

Prevents usage of enhancement prefixes in class and file names that indicate
architectural violations. These names suggest unnecessary abstraction layers
or versioning anti-patterns:
- Enhanced* / *Enhanced - indicates unnecessary wrapper classes
- Simple* / *Simple - defeats the purpose of proper typing
- Consolidated* / *Consolidated - indicates improper abstraction merging

This enforces proper ONEX framework naming conventions.
"""

import argparse
import ast
import sys
from pathlib import Path


class EnhancementPrefixDetector(ast.NodeVisitor):
    """AST visitor to detect enhancement prefix anti-patterns in Python code."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[tuple[int, str, str]] = []
        self.banned_patterns = [
            ("Enhanced", "prefix/suffix"),
            ("Simple", "prefix/suffix"),
            ("Consolidated", "prefix/suffix"),
        ]

    def _check_name(self, name: str, line_num: int, context: str) -> None:
        """Check if a name contains banned enhancement patterns."""
        for pattern, pattern_type in self.banned_patterns:
            # Check prefix: Enhanced*, Simple*, Consolidated*
            if name.startswith(pattern):
                self.violations.append(
                    (
                        line_num,
                        f"{context} '{name}' uses banned {pattern_type} '{pattern}*'",
                        name,
                    )
                )
                continue

            # Check suffix: *Enhanced, *Simple, *Consolidated
            if name.endswith(pattern):
                self.violations.append(
                    (
                        line_num,
                        f"{context} '{name}' uses banned {pattern_type} '*{pattern}'",
                        name,
                    )
                )
                continue

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class names for enhancement patterns."""
        self._check_name(node.name, node.lineno, "Class")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function names for enhancement patterns."""
        self._check_name(node.name, node.lineno, "Function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function names for enhancement patterns."""
        self._check_name(node.name, node.lineno, "Async function")
        self.generic_visit(node)


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """
    Check a Python file for enhancement prefix anti-patterns.

    Args:
        filepath: Path to the Python file to check

    Returns:
        List of (line_number, message, name) tuples for violations found
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        detector = EnhancementPrefixDetector(str(filepath))
        detector.visit(tree)

        return detector.violations

    except SyntaxError as e:
        # Skip files with syntax errors (they'll be caught by other tools)
        return []
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def check_filename(filepath: Path) -> list[str]:
    """
    Check if filename contains enhancement patterns.

    Args:
        filepath: Path to check

    Returns:
        List of violation messages
    """
    violations = []
    filename = filepath.stem  # Get filename without extension

    # Check for enhancement patterns in filename
    banned_patterns = [
        ("enhanced", "prefix/suffix"),
        ("simple", "prefix/suffix"),
        ("consolidated", "prefix/suffix"),
    ]

    for pattern, pattern_type in banned_patterns:
        # Check prefix: enhanced_*, simple_*, consolidated_*
        if filename.lower().startswith(pattern + "_"):
            violations.append(
                f"Filename '{filepath.name}' uses banned {pattern_type} '{pattern}_*'"
            )
            continue

        # Check suffix: *_enhanced, *_simple, *_consolidated
        if filename.lower().endswith("_" + pattern):
            violations.append(
                f"Filename '{filepath.name}' uses banned {pattern_type} '*_{pattern}'"
            )
            continue

    return violations


def main() -> int:
    """Main entry point for validation script."""
    parser = argparse.ArgumentParser(
        description="Detect enhancement prefix anti-patterns in Python code"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to check",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Collect all Python files to check
    files_to_check: list[Path] = []
    for path in args.paths:
        if path.is_file() and path.suffix == ".py":
            files_to_check.append(path)
        elif path.is_dir():
            files_to_check.extend(path.rglob("*.py"))

    if not files_to_check:
        print("No Python files found to check")
        return 0

    total_violations = 0
    files_with_violations = 0

    for filepath in sorted(files_to_check):
        # Check filename
        filename_violations = check_filename(filepath)
        if filename_violations:
            print(f"\n{filepath}:")
            for msg in filename_violations:
                print(f"  - {msg}")
            total_violations += len(filename_violations)
            files_with_violations += 1

        # Check file content
        code_violations = check_file(filepath)
        if code_violations:
            if not filename_violations:
                print(f"\n{filepath}:")
            for line_num, msg, name in sorted(code_violations):
                print(f"  Line {line_num}: {msg}")
            total_violations += len(code_violations)
            if not filename_violations:
                files_with_violations += 1

    if total_violations > 0:
        print(
            f"\n❌ Found {total_violations} enhancement prefix violations "
            f"in {files_with_violations} file(s)"
        )
        print("\nGuidance:")
        print("  - Replace 'Enhanced*' with specific capability names")
        print("  - Remove 'Simple*' and use proper typing instead")
        print("  - Replace 'Consolidated*' with descriptive names")
        print("\nExamples:")
        print("  ❌ EnhancedContainer → ✓ CachedContainer")
        print("  ❌ SimpleValidator → ✓ BasicValidator or just Validator")
        print("  ❌ ConsolidatedService → ✓ UnifiedService or MergedService")
        return 1

    if args.verbose:
        print(f"✓ Checked {len(files_to_check)} files - no violations found")

    return 0


if __name__ == "__main__":
    sys.exit(main())
