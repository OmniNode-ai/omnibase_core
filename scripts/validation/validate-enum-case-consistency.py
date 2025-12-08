#!/usr/bin/env python3
"""
ONEX Enum Case Consistency Validator

This validation script enforces consistent case formatting for enum string values
to maintain code quality and consistency across the ONEX framework.

Usage:
    python validate-enum-case-consistency.py [--max-violations MAX] [--strict] [--quiet] [--help]

Exit Codes:
    0: No violations found or within acceptable limits
    1: Violations found that exceed the maximum threshold

This validator is part of the ONEX validation framework and ensures enum values
follow consistent lowercase formatting unless explicitly exempted.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import TypedDict


class Violation(TypedDict):
    file: str
    line: int
    enum_name: str
    current_value: str
    suggested_value: str
    class_name: str


class EnumCaseValidator:
    """Validates enum string value case consistency."""

    def __init__(self, max_violations: int = 0, strict_mode: bool = False):
        self.max_violations = max_violations
        self.strict_mode = strict_mode
        self.violations: list[Violation] = []

        # Patterns for legitimate uppercase values (cloud instance types, etc.)
        self.exempted_patterns = [
            # Cloud instance types (AWS, Azure, GCP)
            r"^[A-Z]\d+[a-z]*$",  # B1s, D2s, etc.
            r"^[a-z]\d+\.[a-z]+$",  # t2.micro, t3.small, etc.
            r"^[A-Z]\d+[a-z]*_v\d+$",  # D2s_v3, D4s_v3, etc.
            # Standard acronyms that should remain uppercase
            r"^[A-Z]{2,5}$",  # HTTP, REST, API, JSON, etc.
        ]
        self.compiled_patterns = [
            re.compile(pattern) for pattern in self.exempted_patterns
        ]

    def is_exempted_value(self, value: str) -> bool:
        """Check if a value is exempted from lowercase requirements."""
        return any(pattern.match(value) for pattern in self.compiled_patterns)

    def has_uppercase_content(self, value: str) -> bool:
        """Check if string contains uppercase letters."""
        return any(c.isupper() for c in value)

    def analyze_enum_file(self, file_path: Path) -> None:
        """Analyze a single enum file for case consistency violations."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this is an enum class
                    is_enum = any(
                        (
                            (
                                isinstance(base, ast.Name)
                                and ("Enum" in base.id or base.id.endswith("Flag"))
                            )
                            or (
                                isinstance(base, ast.Attribute)
                                and (
                                    base.attr.endswith("Enum")
                                    or base.attr.endswith("Flag")
                                )
                            )
                        )
                        for base in node.bases
                    )

                    if is_enum:
                        self._check_enum_class(node, file_path)

        except (OSError, UnicodeDecodeError, SyntaxError) as e:
            print(f"Error analyzing {file_path}: {e}", file=sys.stderr)

    def _check_enum_class(self, class_node: ast.ClassDef, file_path: Path) -> None:
        """Check enum class for case consistency violations."""
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                # Look for enum value assignments
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        # This is an enum constant (uppercase name)
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            enum_value = node.value.value

                            # Check if the string value has uppercase content
                            if self.has_uppercase_content(
                                enum_value
                            ) and not self.is_exempted_value(enum_value):
                                self.violations.append(
                                    {
                                        "file": str(file_path),
                                        "line": node.lineno,
                                        "enum_name": target.id,
                                        "current_value": enum_value,
                                        "suggested_value": enum_value.lower(),
                                        "class_name": class_node.name,
                                    }
                                )

    def validate_directory(self, directory: Path) -> None:
        """Validate all enum files in a directory."""
        if not directory.exists():
            print(f"❌ ERROR: Directory does not exist: {directory}")
            sys.exit(1)

        enum_files = list(directory.glob("**/enum_*.py"))
        # Sort files for deterministic order across different systems
        enum_files.sort(key=lambda p: str(p))

        if not enum_files:
            print(f"No enum files found in {directory}")
            return

        for file_path in enum_files:
            self.analyze_enum_file(file_path)

    def generate_report(self) -> None:
        """Generate and print violation report."""
        print("🔍 ONEX Enum Case Consistency Validation Report")
        print("=" * 55)

        if not self.violations:
            print("✅ SUCCESS: No enum case consistency violations found")
            print("All enum string values follow consistent lowercase formatting")
            return

        # Group violations by file
        violations_by_file: dict[str, list[Violation]] = {}
        for violation in self.violations:
            file_path = violation["file"]
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append(violation)

        # Sort violations by file and line number for reproducible output
        for file_path, violations in violations_by_file.items():
            violations.sort(key=lambda v: v["line"])

        print(f"Found {len(self.violations)} enum case consistency violations:\n")

        # Process files in sorted order for deterministic output
        for file_path in sorted(violations_by_file.keys()):
            file_violations = violations_by_file[file_path]
            # Use reliable relative path computation with Path APIs
            try:
                relative_path = str(Path(file_path).relative_to(Path.cwd()))
            except ValueError:
                relative_path = file_path
            print(f"📁 {relative_path}")

            for violation in file_violations:
                print(
                    f"  🚨 Line {violation['line']}: {violation['class_name']}.{violation['enum_name']}"
                )
                print(f'     Current:   "{violation["current_value"]}"')
                print(f'     Suggested: "{violation["suggested_value"]}"')
                print("     💡 Use lowercase for consistency with ONEX standards")
                print()

        # Summary
        violation_count = len(self.violations)
        if self.max_violations == 0:
            print(
                f"❌ FAILURE: {violation_count} violations found (zero tolerance policy)"
            )
            print("🔧 Fix all enum values to use consistent lowercase formatting")
        elif violation_count > self.max_violations:
            print(
                f"❌ FAILURE: {violation_count} violations exceed maximum of {self.max_violations}"
            )
            print(f"🔧 Reduce violations by {violation_count - self.max_violations}")
        else:
            print(
                f"⚠️  WARNING: {violation_count} violations found (within limit of {self.max_violations})"
            )

        print("\n📚 EXEMPTED PATTERNS:")
        print("The following patterns are automatically exempted:")
        for pattern in self.exempted_patterns:
            print(f"  • {pattern}")
        print("  Examples: t2.micro, B1s, D2s_v3, HTTP, REST")


def main():
    parser = argparse.ArgumentParser(
        description="Validate enum case consistency in ONEX framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "path", nargs="?", default="src", help="Path to analyze (default: src)"
    )

    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations (default: 0 for zero tolerance)",
    )

    parser.add_argument(
        "--strict", action="store_true", help="Enable strict mode (no exemptions)"
    )

    parser.add_argument(
        "--quiet", action="store_true", help="Suppress output except for errors"
    )

    args = parser.parse_args()

    validator = EnumCaseValidator(
        max_violations=args.max_violations, strict_mode=args.strict
    )

    # Validate the specified directory
    path = Path(args.path)
    validator.validate_directory(path)

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
