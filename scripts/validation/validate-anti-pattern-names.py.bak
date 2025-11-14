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
- "main" - indicates poor module organization

This enforces proper naming conventions in the ONEX framework.
"""

import argparse
import ast
import re
import sys
from pathlib import Path


class AntiPatternNameDetector(ast.NodeVisitor):
    """AST visitor to detect anti-pattern names in Python code."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[tuple[int, str, str]] = []
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
            "main",
            "remaining",
        ]
        self.in_enum_class = False
        self.current_class_name = None

    def _check_name(self, name: str, line_num: int, context: str) -> None:
        """Check if a name contains banned words."""
        name_lower = name.lower()
        for banned_word in self.banned_words:
            # Use word boundary checking to avoid false positives
            # (e.g., "main" shouldn't match "remaining")
            if self._contains_word_boundary(name_lower, banned_word):
                # Skip legitimate uses of "remaining" in time/duration contexts
                if (
                    banned_word == "remaining"
                    and self._is_legitimate_remaining_context(name)
                ):
                    continue

                # Skip legitimate uses of "main" in specific contexts
                if banned_word == "main" and self._is_legitimate_main_context(name):
                    continue

                self.violations.append(
                    (
                        line_num,
                        f"{context} '{name}' contains banned word '{banned_word}'",
                        name,
                    )
                )

    def _contains_word_boundary(self, name_lower: str, banned_word: str) -> bool:
        """Check if banned word appears with proper word boundaries."""

        # Create regex pattern that matches the banned word with appropriate boundaries
        # This handles underscores and camelCase properly while preventing false positives
        # like "main" matching in "remaining"
        # Use word boundaries but also consider underscore boundaries and camelCase
        patterns = [
            # Standard word boundary (for space/punctuation separated)
            r"\b" + re.escape(banned_word) + r"\b",
            # Underscore boundary (for snake_case)
            r"(?:^|_)" + re.escape(banned_word) + r"(?:_|$)",
            # Start of string boundary
            r"^" + re.escape(banned_word) + r"(?=_|$|[a-z])",
        ]

        return any(bool(re.search(pattern, name_lower)) for pattern in patterns)

    def _is_legitimate_remaining_context(self, name: str) -> bool:
        """Check if 'remaining' usage is legitimate in time/duration context."""
        name_lower = name.lower()
        legitimate_patterns = [
            "remaining_time",
            "remaining_seconds",
            "remaining_ms",
            "remaining_duration",
            "time_remaining",
            "get_remaining",
            "has_retries_remaining",
            "estimated_remaining",
            "remaining_attempts",
            "retry_remaining",
            # Single 'remaining' is also legitimate in time contexts
            "remaining",
        ]

        # Check if it's in a time/duration context file
        time_duration_files = [
            "model_time_based",
            "model_progress",
            "model_timeout",
            "model_duration",
            "model_retry_policy",
            "progress_original",
            "timeout_original",
            "duration_original",
        ]

        filename = self.filepath.lower()
        is_time_file = any(time_file in filename for time_file in time_duration_files)

        if is_time_file and any(
            pattern in name_lower for pattern in legitimate_patterns
        ):
            return True

        # Also allow specific non-time patterns
        non_time_patterns = [
            "get_remaining",
            "has_retries_remaining",
            "retries_remaining",
        ]
        return any(pattern in name_lower for pattern in non_time_patterns)

    def _is_legitimate_main_context(self, name: str) -> bool:
        """Check if 'main' usage is legitimate in specific contexts."""
        name_lower = name.lower()
        legitimate_main_patterns = [
            "main_value",  # Primary value in configuration/validation
            "maintenance",  # Maintenance operations
            "domain",  # Domain name patterns
        ]
        return any(pattern in name_lower for pattern in legitimate_main_patterns)

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

                # Skip enum constants (all uppercase or in enum class)
                if target_name.isupper() or self.in_enum_class:
                    continue

                # Check for type aliases (but allow legitimate TypeVar definitions and Union types)
                if (
                    target_name[0].isupper()
                    and not target_name.startswith("Model")
                    and not self._is_legitimate_type_definition(node)
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
                else:
                    self._check_name(target_name, node.lineno, "Variable")
        self.generic_visit(node)

    def _is_legitimate_type_definition(self, node: ast.Assign) -> bool:
        """Check if this is a legitimate type definition (TypeVar, Union, etc.)."""
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                # Allow TypeVar definitions
                if node.value.func.id == "TypeVar":
                    return True

        # Allow Union type aliases - these are legitimate
        if isinstance(node.value, ast.Subscript):
            if (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id == "Union"
            ):
                return True

        return False

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check for type aliases (annotated assignments)."""
        if isinstance(node.target, ast.Name):
            target_name = node.target.id

            # Skip enum constants and legitimate type definitions
            if target_name.isupper() or self.in_enum_class:
                self.generic_visit(node)
                return

            # Check if this looks like a problematic type alias
            if (
                target_name[0].isupper()
                and not target_name.startswith("Model")
                and node.value is not None
                and not self._is_legitimate_type_definition_ann(node)
            ):
                self.violations.append(
                    (
                        node.lineno,
                        f"Type alias '{target_name}' detected - use explicit generic types instead",
                        target_name,
                    )
                )
        self.generic_visit(node)

    def _is_legitimate_type_definition_ann(self, node: ast.AnnAssign) -> bool:
        """Check if this is a legitimate annotated type definition."""
        if node.value is None:
            return True  # Just a type annotation, not an alias

        # Similar logic to regular assignments
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                if node.value.func.id == "TypeVar":
                    return True

        if isinstance(node.value, ast.Subscript):
            if (
                isinstance(node.value.value, ast.Name)
                and node.value.value.id == "Union"
            ):
                return True

        return False


def check_file_for_anti_pattern_names(filepath: Path) -> list[tuple[int, str, str]]:
    """Check a single Python file for anti-pattern names."""
    violations = []

    # Check filename itself for anti-patterns
    filename = filepath.stem  # Get filename without extension
    banned_words = [
        "simple",
        "mock",
        "basic",
        "temp",
        "tmp",
        "wrapper",
        "helper",
        "dummy",
        "fake",
        "main",
    ]  # Note: "remaining" not in filename check as it can be legitimate
    for banned_word in banned_words:
        if banned_word in filename.lower():
            violations.append(
                (
                    0,
                    f"Filename contains banned word '{banned_word}': {filepath.name}",
                    "Filename",
                )
            )

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content, filename=str(filepath))
        detector = AntiPatternNameDetector(str(filepath))
        detector.visit(tree)

        violations.extend(detector.violations)
        return violations

    except SyntaxError as e:
        return [(e.lineno or 0, f"Syntax error: {e.msg}", "")]
    except Exception as e:
        return [(0, f"Error parsing file: {e!s}", "")]


def validate_anti_pattern_names(src_dirs: list[str], max_violations: int = 0) -> bool:
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

    print("\n📊 Anti-Pattern Name Validation Summary:")
    print(
        f"   • Files checked: {len(list(Path(src_dirs[0]).rglob('*.py'))) if src_dirs else 0}"
    )
    print(f"   • Files with violations: {files_with_violations}")
    print(f"   • Total violations: {total_violations}")
    print(f"   • Max allowed: {max_violations}")

    if total_violations <= max_violations:
        print("✅ Anti-Pattern Name validation PASSED")
        return True
    else:
        print("❌ Anti-Pattern Name validation FAILED")
        print("\n🔧 How to fix:")
        print("   1. Replace 'simple' with specific, descriptive names")
        print("   2. Replace 'mock' with proper test fixtures")
        print("   3. Replace 'basic' with domain-specific names")
        print("   4. Replace 'helper'/'wrapper' with proper abstractions")
        print("   5. Remove 'temp'/'tmp' and implement proper solutions")
        print("\n   Example fixes:")
        print("   ❌ SimpleConfig → ✅ ModelConfiguration")
        print("   ❌ MockData → ✅ TestFixture")
        print("   ❌ BasicHandler → ✅ EventHandler")
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
