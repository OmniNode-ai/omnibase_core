#!/usr/bin/env python3
"""
ONEX Dict Conversion Anti-Pattern Detection

Detects and prevents usage of to_dict() and from_dict() methods that violate
our pure Pydantic model architecture principles.

Our architecture principles:
- Use Pydantic models everywhere
- No dict conversions (use .model_dump() only for serialization)
- Structured data with proper typing
- Model composition over dict manipulation

ANTI-PATTERNS DETECTED:
❌ def to_dict(self) -> dict[str, Any]:
❌ def from_dict(cls, data: dict[str, Any]):
❌ .to_dict() method calls
❌ .from_dict() method calls

ACCEPTABLE PATTERNS:
✅ .model_dump() for serialization
✅ BaseModel(**data) for creation
✅ Direct model composition
✅ Proper Pydantic field definitions
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Any


class DictConversionDetector(ast.NodeVisitor):
    """AST visitor to detect dict conversion anti-patterns."""

    def __init__(self) -> None:
        self.violations: list[dict[str, Any]] = []
        self.current_file = ""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for to_dict and from_dict method definitions."""
        if node.name in ("to_dict", "from_dict"):
            self.violations.append(
                {
                    "file": self.current_file,
                    "line": node.lineno,
                    "type": "method_definition",
                    "method": node.name,
                    "message": f"Anti-pattern: {node.name}() method definition violates pure Pydantic architecture",
                }
            )

        # Check for dict patterns in return types
        if hasattr(node, "returns") and node.returns:
            self._check_dict_type_annotation(node.returns, node.name, node.lineno)

        self.generic_visit(node)

    def _check_dict_type_annotation(
        self, annotation: ast.AST, context: str, line: int
    ) -> None:
        """Check if type annotation contains dict patterns."""
        # Check for dict[str, Any] or typing.Dict[str, Any]
        if isinstance(annotation, ast.Subscript):
            # Built-in dict or typing.Dict
            if self._is_dict_type(annotation.value):
                if self._is_str_any_dict_pattern(annotation):
                    self.violations.append(
                        {
                            "file": self.current_file,
                            "line": line,
                            "type": "dict_any_return",
                            "method": context,
                            "message": f"Anti-pattern: {context} returns dict[str, Any] - use Pydantic model instead",
                        }
                    )

            # Check for Optional[dict[...]] or Union[dict[...], None] patterns
            elif self._is_optional_or_union(annotation.value):
                for arg in self._get_union_args(annotation):
                    if isinstance(arg, ast.Subscript) and self._is_dict_type(arg.value):
                        if self._is_str_any_dict_pattern(arg):
                            self.violations.append(
                                {
                                    "file": self.current_file,
                                    "line": line,
                                    "type": "optional_dict_any_return",
                                    "method": context,
                                    "message": f"Anti-pattern: {context} returns Optional[dict[str, Any]] - use Pydantic model instead",
                                }
                            )

    def _is_dict_type(self, node: ast.AST) -> bool:
        """Check if AST node represents dict or typing.Dict."""
        if isinstance(node, ast.Name):
            return node.id == "dict"
        elif isinstance(node, ast.Attribute):
            # Handle typing.Dict
            return (
                isinstance(node.value, ast.Name)
                and node.value.id == "typing"
                and node.attr == "Dict"
            )
        return False

    def _is_optional_or_union(self, node: ast.AST) -> bool:
        """Check if AST node represents Optional or Union from typing."""
        if isinstance(node, ast.Name):
            return node.id in ("Optional", "Union")
        elif isinstance(node, ast.Attribute):
            return (
                isinstance(node.value, ast.Name)
                and node.value.id == "typing"
                and node.attr in ("Optional", "Union")
            )
        return False

    def _get_union_args(self, annotation: ast.Subscript) -> list[ast.AST]:
        """Get arguments from Union or Optional type annotation."""
        if isinstance(annotation.slice, ast.Tuple):
            return annotation.slice.elts
        else:
            # For Optional[T], it's equivalent to Union[T, None]
            return [annotation.slice]

    def _is_str_any_dict_pattern(self, dict_annotation: ast.Subscript) -> bool:
        """Check if dict annotation is dict[str, Any] pattern."""
        if (
            isinstance(dict_annotation.slice, ast.Tuple)
            and len(dict_annotation.slice.elts) == 2
        ):
            key_type = dict_annotation.slice.elts[0]
            value_type = dict_annotation.slice.elts[1]

            return (
                isinstance(key_type, ast.Name)
                and key_type.id == "str"
                and isinstance(value_type, ast.Name)
                and value_type.id == "Any"
            )
        return False

    def visit_Call(self, node: ast.Call) -> None:
        """Check for to_dict() and from_dict() method calls."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("to_dict", "from_dict"):
                self.violations.append(
                    {
                        "file": self.current_file,
                        "line": node.lineno,
                        "type": "method_call",
                        "method": node.func.attr,
                        "message": f"Anti-pattern: .{node.func.attr}() call violates pure Pydantic architecture",
                    }
                )

        self.generic_visit(node)

    def check_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Check a single Python file for dict conversion anti-patterns."""
        self.current_file = str(file_path)
        self.violations = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Parse and visit the AST
            tree = ast.parse(content)
            self.visit(tree)

        except (SyntaxError, UnicodeDecodeError):
            # Skip files with syntax errors or encoding issues
            pass
        except (OSError, ValueError) as e:
            print(f"Warning: Could not process {file_path}: {e}", file=sys.stderr)

        return self.violations


def find_python_files(directory: Path, exclude_patterns: list[str]) -> list[Path]:
    """Find all Python files, excluding specified patterns.

    Returns files in deterministic order for stable CI output.
    """
    python_files = []

    for py_file in directory.rglob("*.py"):
        # Check if file matches any exclude pattern
        file_str = str(py_file)
        should_exclude = any(pattern in file_str for pattern in exclude_patterns)

        if not should_exclude:
            python_files.append(py_file)

    # Sort files by path for deterministic order across different systems
    python_files.sort(key=lambda p: str(p))
    return python_files


def main() -> int:
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Detect dict conversion anti-patterns in Python files"
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
        print(f"❌ Directory {base_dir} does not exist")
        return 1

    # Find Python files
    python_files = find_python_files(base_dir, exclude_patterns)

    if not python_files:
        print("✅ No Python files found to check")
        return 0

    # Check each file
    detector = DictConversionDetector()
    all_violations = []

    for py_file in python_files:
        violations = detector.check_file(py_file)
        all_violations.extend(violations)

    # Report results
    violation_count = len(all_violations)

    if violation_count == 0:
        print("✅ No dict conversion anti-patterns detected")
        return 0

    print(f"❌ Found {violation_count} dict conversion anti-pattern violation(s):")
    print()

    # Group violations by file
    violations_by_file = {}
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

        print(f"❌ {display_path}")
        for violation in violations:
            print(f"   Line {violation['line']}: {violation['message']}")
        print()

    print("🔧 FIXES:")
    print("1. Replace to_dict() methods with direct model access")
    print("2. Replace from_dict() methods with BaseModel(**data)")
    print("3. Use .model_dump() only for final serialization")
    print("4. Compose models instead of converting to dicts")
    print("5. Use Pydantic validation instead of dict manipulation")
    print()
    print("📚 Architecture principle: Pure Pydantic models > Dict conversions")

    # Check against limit
    if violation_count > args.max_violations:
        print(
            f"❌ Violation count ({violation_count}) exceeds maximum allowed ({args.max_violations})"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
