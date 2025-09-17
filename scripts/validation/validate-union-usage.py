#!/usr/bin/env python3
"""
Generic Union type usage validation for omni* repositories.
Validates that Union types are used properly according to ONEX standards.
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set


class UnionUsageChecker(ast.NodeVisitor):
    """Check for Union type usage patterns."""

    def __init__(self):
        self.union_count = 0
        self.issues = []

    def visit_Subscript(self, node):
        """Visit subscript nodes (e.g., Union[str, int])."""
        if isinstance(node.value, ast.Name) and node.value.id == "Union":
            self.union_count += 1

            # Check for Union with None (should use Optional or | None)
            if isinstance(node.slice, ast.Tuple) and len(node.slice.elts) == 2:
                for elt in node.slice.elts:
                    if isinstance(elt, ast.Constant) and elt.value is None:
                        self.issues.append(
                            f"Line {node.lineno}: Use Optional[T] or T | None instead of Union[T, None]"
                        )
                    elif isinstance(elt, ast.Name) and elt.id == "None":
                        self.issues.append(
                            f"Line {node.lineno}: Use Optional[T] or T | None instead of Union[T, None]"
                        )

        self.generic_visit(node)


def validate_python_file(file_path: Path) -> tuple[int, List[str]]:
    """Validate Union usage in a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content, filename=str(file_path))
        checker = UnionUsageChecker()
        checker.visit(tree)

        return checker.union_count, checker.issues

    except Exception as e:
        return 0, [f"Error parsing {file_path}: {e}"]


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate Union type usage")
    parser.add_argument(
        "--max-unions", type=int, default=100, help="Maximum allowed Union types"
    )
    parser.add_argument("path", nargs="?", default=".", help="Path to validate")
    args = parser.parse_args()

    base_path = Path(args.path)
    python_files = list(base_path.rglob("*.py"))

    # Filter out archived files and __pycache__
    python_files = [
        f
        for f in python_files
        if "/archived/" not in str(f)
        and "archived" not in f.parts
        and "__pycache__" not in str(f)
    ]

    if not python_files:
        print("✅ Union validation: No Python files to validate")
        return 0

    total_unions = 0
    total_issues = []

    for py_file in python_files:
        union_count, issues = validate_python_file(py_file)
        total_unions += union_count

        if issues:
            total_issues.extend([f"{py_file}: {issue}" for issue in issues])

    # Report results
    if total_issues:
        print(f"❌ Union validation issues found:")
        for issue in total_issues:
            print(f"   {issue}")

    if total_unions > args.max_unions:
        print(f"❌ Union count exceeded: {total_unions} > {args.max_unions}")
        return 1

    if total_issues:
        return 1

    print(
        f"✅ Union validation: {total_unions} unions in {len(python_files)} files (limit: {args.max_unions})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
