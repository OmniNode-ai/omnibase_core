#!/usr/bin/env python3
"""
ONEX Dict Methods Anti-Pattern Detection

Prevents usage of from_dict, to_dict, and from_legacy_dict methods.
We use ONLY Pydantic serialization with .model_dump() and .model_validate().

This is part of the ONEX Framework validation pipeline.
"""

import argparse
import ast
import sys
from pathlib import Path


def find_dict_method_violations(file_path: Path) -> list[tuple[int, str]]:
    """
    Find dict method anti-patterns in a Python file using AST parsing.

    Banned patterns:
    - def from_dict(
    - def to_dict(
    - def from_legacy_dict(
    - async def from_dict(
    - async def to_dict(
    - async def from_legacy_dict(
    - @classmethod ... from_dict
    - @classmethod ... to_dict
    - @classmethod ... from_legacy_dict
    """
    violations = []
    banned_methods = {"from_dict", "to_dict", "from_legacy_dict"}

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        lines = content.split("\n")

        class DictMethodVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._check_method(node, is_async=False)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._check_method(node, is_async=True)
                self.generic_visit(node)

            def _check_method(
                self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool
            ) -> None:
                if node.name in banned_methods:
                    # Check if it's a classmethod by examining decorator stack
                    has_classmethod = self._has_classmethod_decorator(
                        node.decorator_list
                    )

                    # Get the line content for reporting
                    line_content = (
                        lines[node.lineno - 1].strip()
                        if node.lineno <= len(lines)
                        else ""
                    )

                    # Create descriptive violation message
                    method_type = "async " if is_async else ""
                    decorator_info = "@classmethod " if has_classmethod else ""
                    violation_desc = (
                        f"{decorator_info}{method_type}def {node.name}(...)"
                    )

                    violations.append(
                        (node.lineno, f"{line_content} [{violation_desc}]")
                    )

            def _has_classmethod_decorator(self, decorators: list[ast.expr]) -> bool:
                """Check if any decorator in the stack is @classmethod."""
                for decorator in decorators:
                    if (
                        isinstance(decorator, ast.Name)
                        and decorator.id == "classmethod"
                    ) or (
                        isinstance(decorator, ast.Attribute)
                        and decorator.attr == "classmethod"
                    ):
                        return True
                return False

        visitor = DictMethodVisitor()
        visitor.visit(tree)

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []
    except (OSError, ValueError) as e:
        print(f"Error parsing {file_path}: {e}")
        return []

    return violations


def validate_path(path: Path, max_violations: int = 0) -> bool:
    """Validate a file or directory for dict method anti-patterns."""
    total_violations = 0
    violation_files = []

    if path.is_file():
        # Single file validation
        if path.suffix == ".py":
            violations = find_dict_method_violations(path)
            if violations:
                violation_files.append((path, violations))
                total_violations += len(violations)
    elif path.is_dir():
        # Directory validation - find all Python files
        py_files = list(path.rglob("*.py"))
        # Sort files for deterministic order across different systems
        py_files.sort(key=lambda p: str(p))

        for py_file in py_files:
            # Skip test files and excluded directories
            if any(
                part in str(py_file)
                for part in ["test_", "tests/", "archive/", "archived/", "scripts/"]
            ):
                continue

            violations = find_dict_method_violations(py_file)
            if violations:
                # Sort violations by line number for reproducible output
                violations.sort(key=lambda v: v[0])
                violation_files.append((py_file, violations))
                total_violations += len(violations)
    else:
        print(f"Error: Path {path} is neither a file nor a directory")
        return False

    # Report results
    if total_violations > max_violations:
        print("❌ ONEX Dict Methods Anti-Pattern Detection FAILED")
        print(f"Found {total_violations} violations (max allowed: {max_violations})")
        print()

        # Sort violation files by path for reproducible output
        violation_files.sort(key=lambda item: str(item[0]))

        for file_path, violations in violation_files:
            # Use relative path for cleaner output when possible
            try:
                relative_path = file_path.relative_to(Path.cwd())
                display_path = str(relative_path)
            except ValueError:
                # If relative path computation fails, use absolute path
                display_path = str(file_path)

            print(f"File: {display_path}")
            for line_num, line in violations:
                print(f"  Line {line_num}: {line}")
            print()

        print(
            "❌ SOLUTION: Remove all from_dict, to_dict, and from_legacy_dict methods."
        )
        print("   Use ONLY Pydantic serialization:")
        print("   - .model_dump() for serialization")
        print("   - .model_validate() for deserialization")
        print()
        return False

    print("✅ ONEX Dict Methods Anti-Pattern Detection PASSED")
    print(f"Found {total_violations} violations (max allowed: {max_violations})")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Detect dict method anti-patterns in Python code using AST parsing"
    )
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0)",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="File or directory to scan (default: current directory)",
    )

    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path {path} does not exist")
        sys.exit(1)

    success = validate_path(path, args.max_violations)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
