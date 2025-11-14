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


def validate_dict_any_usage(src_dirs: list[str], max_violations: int = 0) -> bool:
    """
    Validate dict[str, Any] usage across source directories.

    Args:
        src_dirs: list of source directories to check
        max_violations: Maximum allowed violations (default: 0)

    Returns:
        True if violations are within limit, False otherwise
    """
    total_violations = 0
    files_with_violations = 0

    for src_dir in src_dirs:
        src_path = Path(src_dir)
        if not src_path.exists():
            print(f"❌ Source directory not found: {src_dir}")
            continue

        python_files = list(src_path.rglob("*.py"))

        for filepath in python_files:
            # Skip test files, validation scripts, and archived directories
            filepath_str = str(filepath)
            if (
                "/tests/" in filepath_str
                or "/scripts/validation/" in filepath_str
                or "/archive/" in filepath_str
                or "/archived/" in filepath_str
            ):
                continue

            violations = check_file_for_dict_any(filepath)

            if violations:
                files_with_violations += 1
                total_violations += len(violations)

                print(f"❌ {filepath}")
                for line_num, message in violations:
                    print(f"   Line {line_num}: {message}")

    print("\n📊 dict[str, Any] Validation Summary:")
    print(
        f"   • Files checked: {len(list(Path(src_dirs[0]).rglob('*.py'))) if src_dirs else 0}"
    )
    print(f"   • Files with violations: {files_with_violations}")
    print(f"   • Total violations: {total_violations}")
    print(f"   • Max allowed: {max_violations}")

    if total_violations <= max_violations:
        print("✅ dict[str, Any] validation PASSED")
        return True
    else:
        print("❌ dict[str, Any] validation FAILED")
        print("\n🔧 How to fix:")
        print("   1. Replace dict[str, Any] with specific typed models")
        print("   2. Use TypedDict for structured dictionaries")
        print("   3. Use Union types for mixed value types")
        print(
            "   4. If absolutely necessary, use @allow_dict_any decorator with justification"
        )
        print("\n   Example fixes:")
        print("   ❌ metadata: dict[str, Any]")
        print("   ✅ metadata: ModelMetadata")
        print("   ✅ metadata: dict[str, str | int | bool]")
        return False


def main():
    """Main entry point for dict[str, Any] validation."""
    parser = argparse.ArgumentParser(
        description="Validate dict[str, Any] usage in Python source code"
    )
    parser.add_argument(
        "src_dirs",
        nargs="*",
        default=["src/omnibase_core"],
        help="Source directories to validate (default: src/omnibase_core)",
    )
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0)",
    )

    args = parser.parse_args()

    success = validate_dict_any_usage(args.src_dirs, args.max_violations)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
