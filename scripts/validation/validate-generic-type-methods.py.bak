#!/usr/bin/env python3
"""
ONEX Generic Type Methods Anti-Pattern Validator

This validation script detects the anti-pattern where classes have both:
1. Generic methods that accept type parameters
2. Type-specific methods that duplicate the generic functionality

This violates ONEX principles of code reuse and proper generic type usage.

Usage:
    python validate-generic-type-methods.py [file_or_directory_path] [--max-violations MAX] [--fix]

Exit Codes:
    0: No violations found or within acceptable limits
    1: Violations found that exceed the maximum threshold

This validator is part of the ONEX validation framework and ensures proper
generic type method usage.
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import TypedDict

# Using built-in generics (Python 3.9+)


class Violation(TypedDict):
    file: str
    line: int
    class_name: str
    generic_methods: str
    type_specific_methods: str
    violation_type: str
    suggestion: str


class GenericTypeMethodValidator:
    """Validates proper usage of generic type methods."""

    def __init__(self, max_violations: int = 0, auto_fix: bool = False):
        self.max_violations = max_violations
        self.auto_fix = auto_fix
        self.violations: list[Violation] = []

        # Pattern: generic method + type-specific methods
        self.generic_method_patterns = [
            "get_typed_value",
            "add_typed_property",
            "set_typed_value",
            "typed_get",
            "typed_set",
        ]

        # Type-specific method patterns that should be replaced by generics
        self.type_specific_patterns = [
            ("get_string", "get_int", "get_float", "get_bool"),
            (
                "add_string_property",
                "add_int_property",
                "add_float_property",
                "add_bool_property",
            ),
            ("set_string", "set_int", "set_float", "set_bool"),
            ("string_value", "int_value", "float_value", "bool_value"),
        ]

    def analyze_class_for_anti_pattern(
        self, class_node: ast.ClassDef, file_path: Path
    ) -> None:
        """Analyze a class for generic type method anti-patterns."""
        methods = []
        generic_methods = []
        type_specific_methods = []

        # Collect all methods (including async methods)
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(node.name)

        # Find generic methods - use exact match or common prefixes to reduce false positives
        for method_name in methods:
            # Check for exact matches or methods that clearly follow generic patterns
            is_generic = False
            for pattern in self.generic_method_patterns:
                if (
                    method_name == pattern
                    or method_name.startswith(pattern + "_")
                    or (
                        pattern in method_name
                        and any(
                            generic_indicator in method_name.lower()
                            for generic_indicator in ["typed", "generic", "_t"]
                        )
                    )
                ):
                    is_generic = True
                    break
            if is_generic:
                generic_methods.append(method_name)

        # Find type-specific method groups
        methods_set = set(methods)
        for pattern_group in self.type_specific_patterns:
            found_in_group = list(methods_set.intersection(pattern_group))
            if len(found_in_group) >= 3:  # At least 3 type-specific methods
                type_specific_methods.extend(found_in_group)

        # Check for anti-pattern: generic method + type-specific methods
        if generic_methods and type_specific_methods:
            self.violations.append(
                {
                    "file": str(file_path),
                    "line": class_node.lineno,
                    "class_name": class_node.name,
                    "generic_methods": ", ".join(generic_methods),
                    "type_specific_methods": ", ".join(
                        type_specific_methods[:5]
                    ),  # Limit display
                    "violation_type": "generic_with_type_specific_methods",
                    "suggestion": f"Use generic method {generic_methods[0]} instead of type-specific methods",
                }
            )

        # Also check for too many type-specific methods without generic
        elif len(type_specific_methods) >= 4 and not generic_methods:
            self.violations.append(
                {
                    "file": str(file_path),
                    "line": class_node.lineno,
                    "class_name": class_node.name,
                    "generic_methods": "none",
                    "type_specific_methods": ", ".join(type_specific_methods[:5]),
                    "violation_type": "missing_generic_method",
                    "suggestion": "Consider adding a generic typed method to reduce code duplication",
                }
            )

    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for generic type method anti-patterns."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.analyze_class_for_anti_pattern(node, file_path)

        except (SyntaxError, UnicodeDecodeError, OSError, ValueError) as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be skipped using path-safe logic.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file should be skipped, False otherwise
        """
        # Convert to relative path for consistent checking
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            # File is not under current directory, use absolute path
            rel_path = file_path

        # Check if file is in a test directory
        if any(part in ["tests", "__pycache__"] for part in rel_path.parts):
            return True

        # Check if file is in validation directory
        if any(part == "validation" for part in rel_path.parts):
            return True

        # Check if filename starts with test_ or ends with _test.py
        filename = file_path.name
        if filename.startswith("test_") or filename.endswith("_test.py"):
            return True

        # Check for conftest.py or other test-related files
        if filename in ["conftest.py", "pytest.ini", "setup.cfg", "tox.ini"]:
            return True

        return False

    def validate_directory(self, directory: Path) -> None:
        """Validate all Python files in a directory."""
        if not directory.exists():
            print(f"❌ ERROR: Directory does not exist: {directory}")
            sys.exit(1)

        python_files = list(directory.glob("**/*.py"))

        if not python_files:
            print(f"No Python files found in {directory}")
            return

        for file_path in python_files:
            # Skip test files and validation scripts using path-safe logic
            if self._should_skip_file(file_path):
                continue
            self.analyze_file(file_path)

    def validate_path(self, path: Path) -> None:
        """
        Validate a path - can be either a single file or directory.

        Args:
            path: Path to validate (file or directory)
        """
        if not path.exists():
            print(f"❌ ERROR: Path does not exist: {path}")
            sys.exit(1)

        if path.is_file():
            # Single file validation
            if path.suffix == ".py":
                if not self._should_skip_file(path):
                    self.analyze_file(path)
                else:
                    print(f"Skipping {path} (matches skip criteria)")
            else:
                print(f"❌ ERROR: {path} is not a Python file")
                sys.exit(1)
        elif path.is_dir():
            # Directory validation
            self.validate_directory(path)
        else:
            print(f"❌ ERROR: {path} is neither a file nor a directory")
            sys.exit(1)

    def generate_report(self) -> None:
        """Generate and print violation report."""
        print("🔍 ONEX Generic Type Methods Anti-Pattern Validation Report")
        print("=" * 65)

        if not self.violations:
            print("✅ SUCCESS: No generic type method anti-patterns found")
            print("All classes use proper generic method patterns")
            return

        # Sort violations deterministically by file path and line number
        sorted_violations = sorted(
            self.violations, key=lambda v: (v["file"], v["line"])
        )

        # Group violations by file
        violations_by_file = {}
        for violation in sorted_violations:
            file_path = violation["file"]
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append(violation)

        print(
            f"Found {len(self.violations)} generic type method anti-pattern violations:\\n"
        )

        # Process files in sorted order for deterministic output
        for file_path in sorted(violations_by_file.keys()):
            file_violations = violations_by_file[file_path]
            relative_path = file_path.replace(str(Path.cwd()), ".")
            print(f"📁 {relative_path}")

            for violation in file_violations:
                print(f"  🚨 Line {violation['line']}: {violation['class_name']}")
                print(f"     Type: {violation['violation_type']}")
                print(f"     Generic methods: {violation['generic_methods']}")
                print(
                    f"     Type-specific methods: {violation['type_specific_methods']}"
                )
                print(f"     💡 {violation['suggestion']}")
                print()

        # Summary
        violation_count = len(self.violations)
        if self.max_violations == 0:
            print(
                f"❌ FAILURE: {violation_count} violations found (zero tolerance policy)"
            )
            print("🔧 Refactor to use generic methods properly")
        elif violation_count > self.max_violations:
            print(
                f"❌ FAILURE: {violation_count} violations exceed maximum of {self.max_violations}"
            )
            print(f"🔧 Reduce violations by {violation_count - self.max_violations}")
        else:
            print(
                f"⚠️  WARNING: {violation_count} violations found (within limit of {self.max_violations})"
            )

        print("\\n🎯 RECOMMENDED PATTERNS:")
        print("✅ Use generic method: get_typed_value(key, type[T], default: T) -> T")
        print("✅ Single add method: add_property(key, value: T, metadata)")
        print("❌ Avoid: get_string(), get_int(), get_float(), get_bool()")
        print("❌ Avoid: add_string_property(), add_int_property(), etc.")


def main():
    parser = argparse.ArgumentParser(
        description="Validate generic type method patterns in ONEX framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "path",
        nargs="?",
        default="src",
        help="File or directory path to analyze (default: src)",
    )

    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0 for zero tolerance)",
    )

    parser.add_argument(
        "--quiet", action="store_true", help="Suppress output except for errors"
    )

    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix violations where possible"
    )

    args = parser.parse_args()

    validator = GenericTypeMethodValidator(
        max_violations=args.max_violations, auto_fix=args.fix
    )

    # Validate the specified path (file or directory)
    path = Path(args.path)
    validator.validate_path(path)

    # Generate report
    if not args.quiet:
        validator.generate_report()

    # Exit with appropriate code
    violation_count = len(validator.violations)

    if violation_count == 0:
        sys.exit(0)
    elif violation_count > validator.max_violations:
        sys.exit(1)
    else:
        # Violations within acceptable limit
        sys.exit(0)


if __name__ == "__main__":
    main()
