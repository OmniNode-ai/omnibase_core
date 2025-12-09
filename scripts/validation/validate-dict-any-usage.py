#!/usr/bin/env python3
"""
ONEX dict[str, Any] Anti-Pattern Detection

This script detects usage of dict[str, Any] anti-patterns in the codebase
and enforces strong typing standards.

dict[str, Any] is considered an anti-pattern because:
- It defeats the purpose of strong typing
- Provides no compile-time safety
- Makes refactoring dangerous
- Hides potential bugs

Exceptions are allowed only with explicit @allow_dict_any decorator
with documented justification.
"""

import argparse
import ast
import re
import sys
from pathlib import Path


class DictAnyDetector(ast.NodeVisitor):
    """AST visitor to detect dict[str, Any] usage patterns."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []
        self.allowed_lines: set[int] = set()

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Check for dict[str, Any] subscript patterns."""
        if isinstance(node.value, ast.Name) and node.value.id == "dict":
            if self._is_str_any_subscription(node.slice):
                line_num = node.lineno
                if line_num not in self.allowed_lines:
                    self.violations.append(
                        (line_num, "dict[str, Any] anti-pattern detected")
                    )
        self.generic_visit(node)

    def _is_str_any_subscription(self, slice_node: ast.expr) -> bool:
        """Check if slice is [str, Any] pattern."""
        if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) == 2:
            first, second = slice_node.elts
            return (
                isinstance(first, ast.Name)
                and first.id == "str"
                and isinstance(second, ast.Name)
                and second.id == "Any"
            )
        return False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for @allow_dict_any decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "allow_dict_any":
                # Allow dict[str, Any] usage in this function
                for stmt in ast.walk(node):
                    if hasattr(stmt, "lineno"):
                        self.allowed_lines.add(stmt.lineno)
        self.generic_visit(node)


def check_file_for_dict_any(filepath: Path) -> list[tuple[int, str]]:
    """Check a single Python file for dict[str, Any] violations."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content, filename=str(filepath))
        detector = DictAnyDetector(str(filepath))
        detector.visit(tree)

        return detector.violations

    except SyntaxError as e:
        return [(e.lineno or 0, f"Syntax error: {e.msg}")]
    except Exception as e:
        return [(0, f"Error parsing file: {e!s}")]


def _should_skip_file(filepath: Path) -> bool:
    """Check if a file should be skipped based on path patterns."""
    filepath_str = str(filepath)
    return (
        "/tests/" in filepath_str
        or "/scripts/validation/" in filepath_str
        or "/archive/" in filepath_str
        or "/archived/" in filepath_str
    )


def _collect_files_from_paths(paths: list[str]) -> list[Path]:
    """
    Collect Python files from a list of paths.

    Handles both individual files and directories:
    - If path is a .py file, include it directly
    - If path is a directory, recursively find all .py files

    Args:
        paths: List of file or directory paths

    Returns:
        List of Path objects for Python files to check
    """
    files_to_check: list[Path] = []

    for path_str in paths:
        path = Path(path_str)

        if not path.exists():
            print(f"Warning: Path not found: {path_str}")
            continue

        if path.is_file():
            # Individual file - include if it's a Python file
            if path.suffix == ".py":
                files_to_check.append(path)
        elif path.is_dir():
            # Directory - recursively find all Python files
            files_to_check.extend(path.rglob("*.py"))

    return files_to_check


def validate_dict_any_usage(
    paths: list[str], max_violations: int = 0, is_file_mode: bool = False
) -> bool:
    """
    Validate dict[str, Any] usage across files or directories.

    Args:
        paths: List of file or directory paths to check
        max_violations: Maximum allowed violations (default: 0)
        is_file_mode: If True, paths are individual files (skip max check for partial scans)

    Returns:
        True if violations are within limit, False otherwise
    """
    total_violations = 0
    files_with_violations = 0
    files_checked = 0

    # Collect all Python files to check
    python_files = _collect_files_from_paths(paths)

    for filepath in python_files:
        # Skip test files, validation scripts, and archived directories
        if _should_skip_file(filepath):
            continue

        files_checked += 1
        violations = check_file_for_dict_any(filepath)

        if violations:
            files_with_violations += 1
            total_violations += len(violations)

            print(f"dict[str, Any] violations in {filepath}")
            for line_num, message in violations:
                print(f"   Line {line_num}: {message}")

    print("\ndict[str, Any] Validation Summary:")
    print(f"   Files checked: {files_checked}")
    print(f"   Files with violations: {files_with_violations}")
    print(f"   Total violations: {total_violations}")

    # In file mode (pre-commit), we only check for new violations (any violation fails)
    # In directory mode, we compare against max_violations threshold
    if is_file_mode:
        print("   Mode: file mode (staged files only)")
        if total_violations == 0:
            print("PASSED: No dict[str, Any] violations in staged files")
            return True
        else:
            print("FAILED: dict[str, Any] violations found in staged files")
            _print_fix_instructions()
            return False
    else:
        print(f"   Max allowed: {max_violations}")
        if total_violations <= max_violations:
            print("PASSED: dict[str, Any] validation passed")
            return True
        else:
            print("FAILED: dict[str, Any] validation failed")
            _print_fix_instructions()
            return False


def _print_fix_instructions() -> None:
    """Print instructions for fixing dict[str, Any] violations."""
    print("\nHow to fix:")
    print("   1. Replace dict[str, Any] with specific typed models")
    print("   2. Use TypedDict for structured dictionaries")
    print("   3. Use Union types for mixed value types")
    print(
        "   4. If absolutely necessary, use @allow_dict_any decorator with justification"
    )
    print("\n   Example fixes:")
    print("   BAD:  metadata: dict[str, Any]")
    print("   GOOD: metadata: ModelMetadata")
    print("   GOOD: metadata: dict[str, str | int | bool]")


def main():
    """Main entry point for dict[str, Any] validation."""
    parser = argparse.ArgumentParser(
        description="Validate dict[str, Any] usage in Python source code"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files or directories to validate (default: src/omnibase_core)",
    )
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0, used in directory mode)",
    )

    args = parser.parse_args()

    # Determine mode based on arguments
    if args.files:
        # Check if any argument is a file (not a directory)
        has_files = any(Path(f).is_file() for f in args.files if Path(f).exists())
        is_file_mode = has_files
        paths = args.files
    else:
        # No arguments - fall back to default directory scan
        is_file_mode = False
        paths = ["src/omnibase_core"]

    success = validate_dict_any_usage(paths, args.max_violations, is_file_mode)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
