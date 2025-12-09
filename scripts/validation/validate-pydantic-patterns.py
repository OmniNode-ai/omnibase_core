#!/usr/bin/env python3
"""
Pydantic Legacy Pattern Validator for ONEX Architecture

Validates that legacy Pydantic v1 patterns are not used in the codebase.
Prevents regression after successful migration to Pydantic v2.

Detects patterns like:
- .dict() calls (should be .model_dump())
- .dict(exclude_none=True) patterns
- Other legacy Pydantic v1 methods

Usage:
    python scripts/validate-pydantic-patterns.py
    python scripts/validate-pydantic-patterns.py --strict
    python scripts/validate-pydantic-patterns.py file1.py file2.py  # Validate specific files
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


class LegacyPattern:
    """Represents a legacy Pydantic pattern."""

    def __init__(self, pattern: str, description: str, replacement: str, severity: str):
        self.pattern = pattern
        self.description = description
        self.replacement = replacement
        self.severity = severity  # 'error' or 'warning'


class PydanticPatternValidator:
    """Validates Pydantic patterns in Python files."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.legacy_patterns = [
            # Core .dict() patterns (HIGH PRIORITY - these are the main regression risk)
            LegacyPattern(
                pattern=r"\.dict\(\s*\)",
                description="Legacy .dict() call",
                replacement=".model_dump()",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.dict\(\s*exclude_none\s*=\s*True\s*\)",
                description="Legacy .dict(exclude_none=True) call",
                replacement=".model_dump(exclude_none=True)",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.dict\(\s*exclude_unset\s*=\s*True\s*\)",
                description="Legacy .dict(exclude_unset=True) call",
                replacement=".model_dump(exclude_unset=True)",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.dict\(\s*by_alias\s*=\s*True\s*\)",
                description="Legacy .dict(by_alias=True) call",
                replacement=".model_dump(by_alias=True)",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.dict\(\s*exclude\s*=",
                description="Legacy .dict(exclude=...) call",
                replacement=".model_dump(exclude=...)",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.dict\(\s*include\s*=",
                description="Legacy .dict(include=...) call",
                replacement=".model_dump(include=...)",
                severity="error",
            ),
            # Other legacy v1 patterns
            LegacyPattern(
                pattern=r"\.json\(\s*exclude_none\s*=\s*True\s*\)",
                description="Legacy .json(exclude_none=True) call",
                replacement=".model_dump_json(exclude_none=True)",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.json\(\s*by_alias\s*=\s*True\s*\)",
                description="Legacy .json(by_alias=True) call",
                replacement=".model_dump_json(by_alias=True)",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.copy\(\s*update\s*=",
                description="Legacy .copy(update=...) call",
                replacement=".model_copy(update=...)",
                severity="error",
            ),
            LegacyPattern(
                pattern=r"\.copy\(\s*deep\s*=\s*True\s*\)",
                description="Legacy .copy(deep=True) call",
                replacement=".model_copy(deep=True)",
                severity="error",
            ),
            # Schema and config patterns (warnings - less critical)
            LegacyPattern(
                pattern=r"\.schema\(\s*\)",
                description="Legacy .schema() call",
                replacement=".model_json_schema()",
                severity="warning",
            ),
            LegacyPattern(
                pattern=r"\.schema_json\(\s*\)",
                description="Legacy .schema_json() call",
                replacement=".model_json_schema()",
                severity="warning",
            ),
            LegacyPattern(
                pattern=r"class\s+Config\s*:",
                description="Legacy Config class (consider model_config)",
                replacement="model_config = ConfigDict(...)",
                severity="warning",
            ),
            # Validator patterns (warnings - need manual review)
            LegacyPattern(
                pattern=r"@validator\s*\(",
                description="Legacy @validator decorator",
                replacement="@field_validator or @model_validator",
                severity="warning",
            ),
            LegacyPattern(
                pattern=r"@root_validator\s*\(",
                description="Legacy @root_validator decorator",
                replacement="@model_validator",
                severity="warning",
            ),
        ]

    def find_legacy_patterns_in_file(
        self, file_path: Path
    ) -> list[tuple[LegacyPattern, int, str]]:
        """
        Find all legacy Pydantic patterns in a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            List of (LegacyPattern, line_number, line_content) tuples
        """
        findings = []

        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    # Skip comments and docstrings
                    stripped = line.strip()
                    if (
                        stripped.startswith(("#", '"""', "'''"))
                        or '"""' in stripped
                        or "'''" in stripped
                    ):
                        continue

                    # Skip test files that might legitimately test legacy patterns
                    if "test_" in str(file_path) and (
                        "legacy" in stripped.lower() or "v1" in stripped.lower()
                    ):
                        continue

                    # Check each pattern
                    for legacy_pattern in self.legacy_patterns:
                        if re.search(legacy_pattern.pattern, line, re.IGNORECASE):
                            # Additional context checks to avoid false positives
                            if self._is_likely_pydantic_usage(line, file_path):
                                findings.append(
                                    (legacy_pattern, line_num, line.strip())
                                )

        except (UnicodeDecodeError, PermissionError) as e:
            print(f"⚠️  Could not read {file_path}: {e}")

        return findings

    def _is_likely_pydantic_usage(self, line: str, file_path: Path) -> bool:
        """
        Determine if a line is likely using Pydantic patterns vs other libraries.

        Args:
            line: The code line to analyze
            file_path: Path to the file being analyzed

        Returns:
            True if likely Pydantic usage, False otherwise
        """
        # Strong indicators this is Pydantic usage
        pydantic_indicators = [
            "BaseModel",
            "model_",  # model_dump, model_copy, etc.
            "Field(",
            "validator",
            "root_validator",
            "@validator",
            "@root_validator",
            "ConfigDict",
        ]

        # Read a few lines around this line for context
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Look at surrounding lines for context (±5 lines)
            start_idx = max(0, len(lines) - 5)
            end_idx = min(len(lines), len(lines) + 5)
            context_lines = lines[start_idx:end_idx]

            context = " ".join(line.strip() for line in context_lines)

            # Check if any Pydantic indicators are in the context
            for indicator in pydantic_indicators:
                if indicator in context:
                    return True

            # Check file-level indicators (imports, etc.)
            file_content = " ".join(lines[:50])  # Check first 50 lines for imports
            if "pydantic" in file_content.lower() or "BaseModel" in file_content:
                return True

        except Exception:
            pass  # If we can't read context, err on the side of reporting

        # If we can't determine context, assume it's Pydantic (safer for preventing regression)
        return True

    def validate_files(self, files: list[Path], allowed_errors: int = 0) -> bool:
        """
        Validate Pydantic patterns in specific files.

        Args:
            files: List of file paths to validate
            allowed_errors: Number of allowed errors before failing (default: 0)

        Returns:
            True if validation passes, False otherwise
        """
        print("🔍 ONEX Pydantic Legacy Pattern Validation")
        print("=" * 55)
        print("📋 Preventing regression of legacy Pydantic v1 patterns")

        # Filter to only Python files that exist
        python_files = [f for f in files if f.suffix == ".py" and f.exists()]
        print(f"📁 Scanning {len(python_files)} Python file(s)...")

        if not python_files:
            print("⚠️  No Python files to validate")
            return True

        total_errors = 0
        total_warnings = 0
        files_with_issues: dict[str, list[tuple[LegacyPattern, int, str]]] = {}

        for py_file in python_files:
            findings = self.find_legacy_patterns_in_file(py_file)
            if findings:
                files_with_issues[str(py_file)] = findings

                # Count errors vs warnings
                for pattern, _, _ in findings:
                    if pattern.severity == "error":
                        total_errors += 1
                    else:
                        total_warnings += 1

        print(
            f"📊 Found {total_errors} errors and {total_warnings} warnings across {len(files_with_issues)} files"
        )

        # Report findings
        if files_with_issues:
            print("\n🚨 FILES WITH LEGACY PYDANTIC PATTERNS:")
            for file_path, findings in files_with_issues.items():
                print(f"\n   📄 {file_path} ({len(findings)} issues):")

                for pattern, line_num, line in findings:
                    severity_icon = "❌" if pattern.severity == "error" else "⚠️"
                    print(
                        f"      {severity_icon} Line {line_num}: {pattern.description}"
                    )
                    print(f"         Code: {line}")
                    print(f"         Fix:  Use {pattern.replacement}")

        # Apply validation rules
        success = True

        if total_errors > allowed_errors:
            print(
                f"\n❌ CRITICAL: Found {total_errors} legacy Pydantic patterns (allowed: {allowed_errors})"
            )
            print(
                "   🚫 REGRESSION DETECTED! These patterns were already migrated to Pydantic v2."
            )
            print("   🔧 Quick fixes:")
            print("      • Replace .dict() with .model_dump()")
            print(
                "      • Replace .dict(exclude_none=True) with .model_dump(exclude_none=True)"
            )
            print("      • Replace .json(...) with .model_dump_json(...)")
            print("      • Replace .copy(...) with .model_copy(...)")
            success = False
        elif total_warnings > 0 and self.strict:
            print(f"\n⚠️  STRICT MODE: {total_warnings} warnings found")
            print("   These patterns should be reviewed and potentially updated:")
            print("      • @validator → @field_validator or @model_validator")
            print("      • @root_validator → @model_validator")
            print("      • Config class → model_config = ConfigDict(...)")
            success = False
        elif total_warnings > 0:
            print(f"\n⚠️  INFO: {total_warnings} warnings found (non-critical)")
            print("   Consider updating these patterns in future refactoring:")
            print("      • Legacy validators and config classes")
            print("      • Schema generation methods")

        # Success message
        if total_errors == 0 and total_warnings == 0:
            print("\n✅ EXCELLENT: No legacy Pydantic patterns found!")
            print("   🎉 Full Pydantic v2 compliance maintained!")

        print("\n📊 PYDANTIC VALIDATION SUMMARY")
        print("=" * 55)
        print(f"Total errors: {total_errors}")
        print(f"Total warnings: {total_warnings}")
        print(f"Files with issues: {len(files_with_issues)}")
        print(f"Allowed errors: {allowed_errors}")
        print(f"Strict mode: {'ON' if self.strict else 'OFF'}")
        print(f"Status: {'PASSED' if success else 'FAILED'}")

        if success and total_errors == 0:
            print("🛡️  Legacy pattern regression protection active!")

        return success

    def validate_project(self, src_dir: Path, allowed_errors: int = 0) -> bool:
        """
        Validate Pydantic patterns across the entire project.

        Args:
            src_dir: Source directory to scan
            allowed_errors: Number of allowed errors before failing (default: 0)

        Returns:
            True if validation passes, False otherwise
        """
        print("🔍 ONEX Pydantic Legacy Pattern Validation")
        print("=" * 55)
        print("📋 Preventing regression of legacy Pydantic v1 patterns")

        # Find all Python files
        python_files = list(src_dir.rglob("*.py"))
        print(f"📁 Scanning {len(python_files)} Python files...")

        return self._validate_files_internal(python_files, allowed_errors, src_dir)

    def _validate_files_internal(
        self,
        python_files: list[Path],
        allowed_errors: int = 0,
        base_dir: Path | None = None,
    ) -> bool:
        """
        Internal method to validate a list of Python files.

        Args:
            python_files: List of Python file paths to validate
            allowed_errors: Number of allowed errors before failing
            base_dir: Base directory for relative path display (optional)

        Returns:
            True if validation passes, False otherwise
        """
        total_errors = 0
        total_warnings = 0
        files_with_issues: dict[str, list[tuple[LegacyPattern, int, str]]] = {}

        for py_file in python_files:
            findings = self.find_legacy_patterns_in_file(py_file)
            if findings:
                # Use relative path if base_dir provided, otherwise use file name
                if base_dir:
                    try:
                        relative_path = py_file.relative_to(base_dir.parent)
                    except ValueError:
                        relative_path = py_file
                else:
                    relative_path = py_file
                files_with_issues[str(relative_path)] = findings

                # Count errors vs warnings
                for pattern, _, _ in findings:
                    if pattern.severity == "error":
                        total_errors += 1
                    else:
                        total_warnings += 1

        print(
            f"📊 Found {total_errors} errors and {total_warnings} warnings across {len(files_with_issues)} files"
        )

        # Report findings
        if files_with_issues:
            print("\n🚨 FILES WITH LEGACY PYDANTIC PATTERNS:")
            for file_path, findings in files_with_issues.items():
                print(f"\n   📄 {file_path} ({len(findings)} issues):")

                for pattern, line_num, line in findings:
                    severity_icon = "❌" if pattern.severity == "error" else "⚠️"
                    print(
                        f"      {severity_icon} Line {line_num}: {pattern.description}"
                    )
                    print(f"         Code: {line}")
                    print(f"         Fix:  Use {pattern.replacement}")

        # Apply validation rules
        success = True

        if total_errors > allowed_errors:
            print(
                f"\n❌ CRITICAL: Found {total_errors} legacy Pydantic patterns (allowed: {allowed_errors})"
            )
            print(
                "   🚫 REGRESSION DETECTED! These patterns were already migrated to Pydantic v2."
            )
            print("   🔧 Quick fixes:")
            print("      • Replace .dict() with .model_dump()")
            print(
                "      • Replace .dict(exclude_none=True) with .model_dump(exclude_none=True)"
            )
            print("      • Replace .json(...) with .model_dump_json(...)")
            print("      • Replace .copy(...) with .model_copy(...)")
            success = False
        elif total_warnings > 0 and self.strict:
            print(f"\n⚠️  STRICT MODE: {total_warnings} warnings found")
            print("   These patterns should be reviewed and potentially updated:")
            print("      • @validator → @field_validator or @model_validator")
            print("      • @root_validator → @model_validator")
            print("      • Config class → model_config = ConfigDict(...)")
            success = False
        elif total_warnings > 0:
            print(f"\n⚠️  INFO: {total_warnings} warnings found (non-critical)")
            print("   Consider updating these patterns in future refactoring:")
            print("      • Legacy validators and config classes")
            print("      • Schema generation methods")

        # Success message
        if total_errors == 0 and total_warnings == 0:
            print("\n✅ EXCELLENT: No legacy Pydantic patterns found!")
            print("   🎉 Full Pydantic v2 compliance maintained!")

        print("\n📊 PYDANTIC VALIDATION SUMMARY")
        print("=" * 55)
        print(f"Total errors: {total_errors}")
        print(f"Total warnings: {total_warnings}")
        print(f"Files with issues: {len(files_with_issues)}")
        print(f"Allowed errors: {allowed_errors}")
        print(f"Strict mode: {'ON' if self.strict else 'OFF'}")
        print(f"Status: {'PASSED' if success else 'FAILED'}")

        if success and total_errors == 0:
            print("🛡️  Legacy pattern regression protection active!")

        return success


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="ONEX Pydantic Legacy Pattern Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate-pydantic-patterns.py              # Check for errors only
    python scripts/validate-pydantic-patterns.py --strict     # Check errors and warnings
    python scripts/validate-pydantic-patterns.py --allow-errors 3  # Allow up to 3 errors
    python scripts/validate-pydantic-patterns.py file1.py file2.py  # Validate specific files
        """,
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to validate (default: scan src/ directory)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Strict mode - treat warnings as errors"
    )
    parser.add_argument(
        "--allow-errors",
        type=int,
        default=0,
        help="Number of allowed errors before failing (default: 0)",
    )
    parser.add_argument(
        "--src-dir",
        "-s",
        type=Path,
        default=Path("src"),
        help="Source directory to scan when no files provided (default: src)",
    )

    args = parser.parse_args()

    validator = PydanticPatternValidator(strict=args.strict)

    # If files are provided, validate only those files
    if args.files:
        files_to_check = [Path(f) for f in args.files if f.endswith(".py")]
        if not files_to_check:
            print("⚠️  No Python files provided to validate")
            sys.exit(0)
        success = validator.validate_files(
            files_to_check, allowed_errors=args.allow_errors
        )
    else:
        # Fall back to scanning src/ directory
        if not args.src_dir.exists():
            print(f"❌ Source directory not found: {args.src_dir}")
            sys.exit(1)
        success = validator.validate_project(
            args.src_dir, allowed_errors=args.allow_errors
        )

    if not success:
        print("\n🚫 Pydantic pattern validation failed!")
        print("💡 Run this script with --help for usage information")
        sys.exit(1)
    else:
        print("\n✅ Pydantic pattern validation passed!")


if __name__ == "__main__":
    main()
