#!/usr/bin/env python3
"""
ONEX Anti-Pattern Name Detection

Prevents usage of anti-pattern names in class, function, and variable names:
- "simple" - defeats the purpose of proper typing
- "mock" - should use proper testing patterns
- "basic" - indicates insufficient abstraction
- "temp" - indicates technical debt
- "tmp" - indicates technical debt
- "wrapper" - usually indicates poor design
- "helper" - often indicates poor organization

This enforces proper naming conventions in the ONEX framework.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple


class AntiPatternNameDetector(ast.NodeVisitor):
    """AST visitor to detect anti-pattern names in Python code."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: List[Tuple[int, str, str]] = []
        self.banned_words = [
            "simple",
            "mock",
            "basic",
            "temp",
            "tmp",
            "wrapper",
            "helper",
            "dummy",
            "fake",
        ]
        self.in_enum_class = False
        self.current_class_name = None

    def _check_name(self, name: str, line_num: int, context: str) -> None:
        """Check if a name contains banned words."""
        name_lower = name.lower()
        for banned_word in self.banned_words:
            if banned_word in name_lower:
                self.violations.append(
                    (
                        line_num,
                        f"{context} '{name}' contains banned word '{banned_word}'",
                        name,
                    )
                )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class names and track enum classes."""
        # Check if this is an enum class
        old_in_enum = self.in_enum_class
        old_class_name = self.current_class_name

        self.current_class_name = node.name
        self.in_enum_class = any(
            isinstance(base, ast.Name) and base.id == "Enum" for base in node.bases
        )

        # Only check class names that are actual anti-patterns
        # Allow enum classes to have any name since they're domain-specific
        if not self.in_enum_class:
            self._check_name(node.name, node.lineno, "Class")

        self.generic_visit(node)

        # Restore previous state
        self.in_enum_class = old_in_enum
        self.current_class_name = old_class_name

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function names (allow legitimate factory methods)."""
        # Skip legitimate factory methods and property accessors
        legitimate_patterns = [
            "create_simple",  # Factory method for simple creation
            "is_simple",  # Property checker
            "to_basic_dict",  # Legacy conversion method
            "get_next_attempt_time",  # Legitimate function names
            "validate_current_attempt",
            "retry_attempts_made",
            "record_attempt",
        ]

        # Skip template-related functions (legitimate domain term)
        if "template" in node.name.lower():
            self.generic_visit(node)
            return

        # Skip if this is a legitimate pattern
        if node.name not in legitimate_patterns:
            self._check_name(node.name, node.lineno, "Function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function names."""
        self._check_name(node.name, node.lineno, "Async function")
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Check variable assignments (skip enum constants and detect type aliases)."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                target_name = target.id

                # Check for type aliases (CamelCase = SomeType pattern)
                if (
                    target_name[0].isupper()
                    and not target_name.startswith("Model")
                    and not target_name.isupper()
                    and not self.in_enum_class
                ):
                    # This looks like a type alias
                    self.violations.append(
                        (
                            node.lineno,
                            f"Type alias '{target_name}' detected - use explicit generic types instead",
                            target_name,
                        )
                    )
                # Check for banned words in regular variables
                elif not (target_name.isupper() or self.in_enum_class):
                    self._check_name(target_name, node.lineno, "Variable")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check for type aliases (annotated assignments)."""
        if isinstance(node.target, ast.Name):
            # Check if this looks like a type alias (usually CamelCase = SomeType)
            target_name = node.target.id
            if (
                target_name[0].isupper()
                and not target_name.startswith("Model")
                and not target_name.isupper()
            ):  # Not enum constant
                self.violations.append(
                    (
                        node.lineno,
                        f"Type alias '{target_name}' detected - use explicit generic types instead",
                        target_name,
                    )
                )
        self.generic_visit(node)


def check_file_for_anti_pattern_names(filepath: Path) -> List[Tuple[int, str, str]]:
    """Check a single Python file for anti-pattern names."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content, filename=str(filepath))
        detector = AntiPatternNameDetector(str(filepath))
        detector.visit(tree)

        return detector.violations

    except SyntaxError as e:
        return [(e.lineno or 0, f"Syntax error: {e.msg}", "")]
    except Exception as e:
        return [(0, f"Error parsing file: {str(e)}", "")]


def validate_anti_pattern_names(src_dirs: List[str], max_violations: int = 0) -> bool:
    """
    Validate anti-pattern names across source directories.

    Args:
        src_dirs: List of source directories to check
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

            violations = check_file_for_anti_pattern_names(filepath)

            if violations:
                files_with_violations += 1
                total_violations += len(violations)

                print(f"❌ {filepath}")
                for line_num, message, name in violations:
                    print(f"   Line {line_num}: {message}")

    print(f"\n📊 Anti-Pattern Name Validation Summary:")
    print(
        f"   • Files checked: {len(list(Path(src_dirs[0]).rglob('*.py'))) if src_dirs else 0}"
    )
    print(f"   • Files with violations: {files_with_violations}")
    print(f"   • Total violations: {total_violations}")
    print(f"   • Max allowed: {max_violations}")

    if total_violations <= max_violations:
        print(f"✅ Anti-Pattern Name validation PASSED")
        return True
    else:
        print(f"❌ Anti-Pattern Name validation FAILED")
        print(f"\n🔧 How to fix:")
        print(f"   1. Replace 'simple' with specific, descriptive names")
        print(f"   2. Replace 'mock' with proper test fixtures")
        print(f"   3. Replace 'basic' with domain-specific names")
        print(f"   4. Replace 'helper'/'wrapper' with proper abstractions")
        print(f"   5. Remove 'temp'/'tmp' and implement proper solutions")
        print(f"\n   Example fixes:")
        print(f"   ❌ SimpleConfig → ✅ ModelConfiguration")
        print(f"   ❌ MockData → ✅ TestFixture")
        print(f"   ❌ BasicHandler → ✅ EventHandler")
        return False


def main():
    """Main entry point for anti-pattern name validation."""
    parser = argparse.ArgumentParser(
        description="Validate anti-pattern names in Python source code"
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

    success = validate_anti_pattern_names(args.src_dirs, args.max_violations)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
