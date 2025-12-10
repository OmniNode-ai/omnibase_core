#!/usr/bin/env python3
"""
ONEX Timestamp Fields Anti-Pattern Detection.

Detects string fields that should be datetime objects, specifically:
- Fields typed as `str` but using `.isoformat()` in default_factory
- Fields typed as `str` with timestamp-like names
- Provides specific suggestions for proper datetime typing

"""

import argparse
import ast
import re
from pathlib import Path
from typing import NamedTuple


class TimestampViolation(NamedTuple):
    """Timestamp field violation details."""

    file_path: Path
    line_number: int
    field_name: str
    current_type: str
    violation_type: str
    suggested_fix: str


class TimestampFieldValidator:
    """Validates proper usage of timestamp fields in Pydantic models."""

    def __init__(self):
        # Patterns that suggest timestamp fields
        self.timestamp_field_patterns = [
            r".*_at$",  # created_at, updated_at
            r".*_time$",  # start_time, end_time
            r".*_timestamp$",  # last_timestamp
            r"^created$",  # created
            r"^updated$",  # updated
            r"^modified$",  # modified
            r"^last_.*$",  # last_modified, last_accessed
        ]

        # Compiled regex patterns
        self.timestamp_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.timestamp_field_patterns
        ]

        self.violations: list[TimestampViolation] = []

    def is_timestamp_field_name(self, field_name: str) -> bool:
        """Check if field name suggests it should be a timestamp."""
        return any(pattern.match(field_name) for pattern in self.timestamp_patterns)

    def validate_file(self, file_path: Path) -> None:
        """Validate timestamp fields in a single file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            self._validate_ast(tree, file_path, content.splitlines())

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"⚠️  Skipping {file_path}: {e}")

    def _validate_ast(self, tree: ast.AST, file_path: Path, lines: list[str]) -> None:
        """Validate AST for timestamp field violations."""

        class TimestampVisitor(ast.NodeVisitor):
            def __init__(self, validator: TimestampFieldValidator):
                self.validator = validator
                self.file_path = file_path
                self.lines = lines

            def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
                """Visit annotated assignments (field definitions)."""
                if isinstance(node.target, ast.Name):
                    field_name = node.target.id

                    # Check if this looks like a timestamp field
                    if self.validator.is_timestamp_field_name(field_name):
                        type_annotation = ast.unparse(node.annotation)

                        # Check for string type on timestamp-like field
                        if "str" in type_annotation:
                            violation_type = "timestamp_field_as_string"
                            suggested_fix = f"Change type from '{type_annotation}' to 'datetime' or 'datetime | None'"

                            self.validator.violations.append(
                                TimestampViolation(
                                    file_path=file_path,
                                    line_number=node.lineno,
                                    field_name=field_name,
                                    current_type=type_annotation,
                                    violation_type=violation_type,
                                    suggested_fix=suggested_fix,
                                )
                            )

                    # Check for .isoformat() usage in default_factory regardless of field name
                    if node.value and isinstance(node.value, ast.Call):
                        if (
                            isinstance(node.value.func, ast.Name)
                            and node.value.func.id == "Field"
                        ):
                            # Check Field arguments for default_factory with .isoformat()
                            for keyword in node.value.keywords:
                                if (
                                    keyword.arg == "default_factory"
                                    and self._contains_isoformat(keyword.value)
                                ):
                                    type_annotation = ast.unparse(node.annotation)
                                    if "str" in type_annotation:
                                        violation_type = "isoformat_with_string_type"
                                        suggested_fix = "Remove .isoformat() and change type to 'datetime'"

                                        self.validator.violations.append(
                                            TimestampViolation(
                                                file_path=file_path,
                                                line_number=node.lineno,
                                                field_name=field_name,
                                                current_type=type_annotation,
                                                violation_type=violation_type,
                                                suggested_fix=suggested_fix,
                                            )
                                        )

                self.generic_visit(node)

            def _contains_isoformat(self, node: ast.AST) -> bool:
                """Check if AST node contains .isoformat() call."""
                if isinstance(node, ast.Lambda):
                    return self._contains_isoformat(node.body)
                elif isinstance(node, ast.Call):
                    if (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr == "isoformat"
                    ):
                        return True
                    return any(self._contains_isoformat(arg) for arg in node.args)
                elif hasattr(node, "body") and isinstance(node.body, list):
                    return any(self._contains_isoformat(item) for item in node.body)
                elif hasattr(node, "body"):
                    return self._contains_isoformat(node.body)
                return False

        visitor = TimestampVisitor(self)
        visitor.visit(tree)

    def validate_directory(self, directory: Path, recursive: bool = True) -> None:
        """Validate all Python files in directory."""
        pattern = "**/*.py" if recursive else "*.py"
        python_files = directory.glob(pattern)

        for file_path in python_files:
            if file_path.is_file() and not self._should_skip_file(file_path):
                self.validate_file(file_path)

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            "__pycache__",
            ".pyc",
            "test_",
            "_test.py",
            "migrations/",
            "venv/",
            ".venv/",
            "node_modules/",
        ]

        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)

    def print_report(self) -> bool:
        """Print validation report and return success status."""
        print("🔍 ONEX Timestamp Fields Anti-Pattern Validation Report")
        print("=" * 60)

        if not self.violations:
            print("✅ SUCCESS: No timestamp field violations found")
            print("All timestamp fields use proper datetime typing")
            return True

        print(f"❌ FAILURE: {len(self.violations)} timestamp field violations found")
        print()

        # Group violations by file
        violations_by_file = {}
        for violation in self.violations:
            if violation.file_path not in violations_by_file:
                violations_by_file[violation.file_path] = []
            violations_by_file[violation.file_path].append(violation)

        for file_path, file_violations in violations_by_file.items():
            print(f"📁 {file_path}")
            for violation in file_violations:
                print(f"  🚨 Line {violation.line_number}: {violation.field_name}")
                print(f"     Current:   {violation.current_type}")
                print(f"     Violation: {violation.violation_type}")
                print(f"     💡 {violation.suggested_fix}")
                print()

        print("🔧 Quick Fix Examples:")
        print(
            "  Before: created_at: str = Field(default_factory=lambda: datetime.now().isoformat())"
        )
        print(
            "  After:  created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))"
        )
        print()
        print("  Before: last_modified: str | None = Field(None)")
        print("  After:  last_modified: datetime | None = Field(None)")

        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate proper timestamp field typing in ONEX models"
    )
    parser.add_argument("path", help="Path to Python file or directory to validate")
    parser.add_argument(
        "--max-violations",
        type=int,
        default=-1,
        help="Maximum allowed violations (default: unlimited)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Recursively scan directories (default: True)",
    )

    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"❌ Error: Path '{path}' does not exist")
        return 1

    validator = TimestampFieldValidator()

    if path.is_file():
        validator.validate_file(path)
    else:
        validator.validate_directory(path, args.recursive)

    success = validator.print_report()

    # Check max violations limit
    if args.max_violations >= 0 and len(validator.violations) > args.max_violations:
        print(
            f"\n❌ VIOLATION LIMIT EXCEEDED: {len(validator.violations)} > {args.max_violations}"
        )
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
