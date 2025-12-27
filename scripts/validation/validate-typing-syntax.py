#!/usr/bin/env python3
"""
ONEX Typing Syntax Validation

This script detects old-style typing syntax and enforces modern typing standards
for Python 3.10+ union syntax.

Old-style patterns that are detected and flagged:
- Optional[Type] → should be Type | None
- Union[Type1, Type2] → should be Type1 | Type2
- Union[Type1, Type2, Type3] → should be Type1 | Type2 | Type3

This ensures consistent use of modern Python typing syntax across the codebase.
"""

import argparse
import ast
import sys
from pathlib import Path


class TypingSyntaxDetector(ast.NodeVisitor):
    """AST visitor to detect old-style typing syntax patterns."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[tuple[int, str]] = []
        self.typing_imports: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Track typing imports."""
        for alias in node.names:
            if alias.name == "typing":
                self.typing_imports.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from typing imports."""
        if node.module == "typing":
            for alias in node.names:
                if alias.name in ("Optional", "Union"):
                    self.typing_imports.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Check for old-style typing patterns."""
        if isinstance(node.value, ast.Name):
            if node.value.id == "Optional":
                self._check_optional_usage(node)
            elif node.value.id == "Union":
                self._check_union_usage(node)
        elif isinstance(node.value, ast.Attribute):
            # Handle typing.Optional and typing.Union
            if (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id in self.typing_imports
                and node.value.attr in ("Optional", "Union")
            ):
                if node.value.attr == "Optional":
                    self._check_optional_usage(node)
                elif node.value.attr == "Union":
                    self._check_union_usage(node)
        self.generic_visit(node)

    def _check_optional_usage(self, node: ast.Subscript) -> None:
        """Check Optional[Type] usage."""
        line_num = node.lineno
        type_hint = self._extract_type_string(node.slice)

        self.violations.append(
            (line_num, f"Optional[{type_hint}] should be {type_hint} | None")
        )

    def _check_union_usage(self, node: ast.Subscript) -> None:
        """Check Union[Type1, Type2, ...] usage."""
        line_num = node.lineno

        if isinstance(node.slice, ast.Tuple):
            types = []
            for elt in node.slice.elts:
                types.append(self._extract_type_string(elt))

            union_types = " | ".join(types)
            original_union = "Union[" + ", ".join(types) + "]"

            self.violations.append(
                (line_num, f"{original_union} should be {union_types}")
            )
        else:
            # Single type in Union (which is unusual but possible)
            type_hint = self._extract_type_string(node.slice)
            self.violations.append(
                (line_num, f"Union[{type_hint}] is unnecessary, just use {type_hint}")
            )

    def _extract_type_string(self, node: ast.expr) -> str:
        """Extract type hint as string from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            # Handle list[str], dict[str, int], etc.
            if isinstance(node.value, ast.Name):
                slice_str = self._extract_type_string(node.slice)
                if isinstance(node.slice, ast.Tuple):
                    slice_parts = [
                        self._extract_type_string(elt) for elt in node.slice.elts
                    ]
                    slice_str = ", ".join(slice_parts)
                return f"{node.value.id}[{slice_str}]"
        elif isinstance(node, ast.Attribute):
            # Handle module.Type patterns
            value_str = self._extract_type_string(node.value)
            return f"{value_str}.{node.attr}"
        elif isinstance(node, ast.Tuple):
            # Handle tuple of types
            return ", ".join(self._extract_type_string(elt) for elt in node.elts)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Handle existing T | U syntax
            left = self._extract_type_string(node.left)
            right = self._extract_type_string(node.right)
            return f"{left} | {right}"

        # Fallback to basic representation
        try:
            return ast.unparse(node)
        except Exception:
            return "Unknown"


def check_file_for_typing_syntax(filepath: Path) -> list[tuple[int, str]]:
    """Check a single Python file for old-style typing syntax."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Skip files that don't contain typing-related imports or usage
        if not any(
            pattern in content
            for pattern in ["Optional[", "Union[", "from typing", "import typing"]
        ):
            return []

        # Parse AST
        tree = ast.parse(content, filename=str(filepath))
        detector = TypingSyntaxDetector(str(filepath))
        detector.visit(tree)

        return detector.violations

    except SyntaxError as e:
        return [(e.lineno or 0, f"Syntax error: {e.msg}")]
    except Exception as e:
        return [(0, f"Error parsing file: {e!s}")]


def validate_typing_syntax(src_dirs: list[str], max_violations: int = 0) -> bool:
    """
    Validate typing syntax across source directories.

    Args:
        src_dirs: List of source directories to check
        max_violations: Maximum allowed violations (default: 0)

    Returns:
        True if violations are within limit, False otherwise
    """
    total_violations = 0
    files_with_violations = 0
    all_python_files = 0

    for src_dir in src_dirs:
        src_path = Path(src_dir)
        if not src_path.exists():
            print(f"❌ Source directory not found: {src_dir}")
            continue

        python_files = list(src_path.rglob("*.py"))
        all_python_files += len(python_files)

        for filepath in python_files:
            # Skip test files, validation scripts, and archived directories
            filepath_str = str(filepath)
            if (
                "/tests/" in filepath_str
                or "/scripts/validation/" in filepath_str
                or "/archive/" in filepath_str
                or "/archived/" in filepath_str
                or "__pycache__" in filepath_str
            ):
                continue

            violations = check_file_for_typing_syntax(filepath)

            if violations:
                files_with_violations += 1
                total_violations += len(violations)

                print(f"❌ {filepath}")
                for line_num, message in violations:
                    print(f"   Line {line_num}: {message}")

    print("\n📊 Typing Syntax Validation Summary:")
    print(f"   • Files checked: {all_python_files}")
    print(f"   • Files with violations: {files_with_violations}")
    print(f"   • Total violations: {total_violations}")
    print(f"   • Max allowed: {max_violations}")

    if total_violations <= max_violations:
        print("✅ Typing syntax validation PASSED")
        return True
    else:
        print("❌ Typing syntax validation FAILED")
        print("\n🔧 How to fix:")
        print("   1. Replace Optional[Type] with Type | None")
        print("   2. Replace Union[Type1, Type2] with Type1 | Type2")
        print("   3. Replace Union[Type1, Type2, Type3] with Type1 | Type2 | Type3")
        print("\n   Example fixes:")
        print("   ❌ value: Optional[str]")
        print("   ✅ value: str | None")
        print("   ❌ data: Union[str, int]")
        print("   ✅ data: str | int")
        print("   ❌ result: Union[str, int, bool]")
        print("   ✅ result: str | int | bool")
        return False


def main():
    """Main entry point for typing syntax validation."""
    parser = argparse.ArgumentParser(
        description="Validate typing syntax usage in Python source code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool detects old-style typing patterns and enforces modern Python 3.10+ syntax:

• Optional[Type] → Type | None
• Union[Type1, Type2] → Type1 | Type2
• Union[Type1, Type2, Type3] → Type1 | Type2 | Type3

This ensures consistent use of modern typing syntax across the codebase.
        """,
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

    success = validate_typing_syntax(args.src_dirs, args.max_violations)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
