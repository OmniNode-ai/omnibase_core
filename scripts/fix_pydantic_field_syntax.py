#!/usr/bin/env python3
"""
Fix Pydantic Field() syntax for Pydantic 2 compatibility.

This script updates Field() syntax from Pydantic 1 to Pydantic 2:
- Old: Field(None, description="...") -> New: Field(default=None, description="...")
- Old: Field(..., description="...") -> Keep as is (required field)
- Old: Field(default_factory=list) -> Keep as is (already Pydantic 2)

This ensures mypy properly recognizes optional fields with defaults.

Usage:
    # Dry run (preview changes)
    poetry run python scripts/fix_pydantic_field_syntax.py --dry-run

    # Fix specific file
    poetry run python scripts/fix_pydantic_field_syntax.py --file src/path/to/file.py

    # Fix all model files
    poetry run python scripts/fix_pydantic_field_syntax.py --all

    # Fix with backup
    poetry run python scripts/fix_pydantic_field_syntax.py --all --backup
"""

import argparse
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FieldFixResult:
    """Result of fixing a Field() definition."""

    file_path: str
    line_number: int
    field_name: str
    original_line: str
    fixed_line: str
    fix_type: str
    success: bool


class PydanticFieldSyntaxFixer:
    """Fixes Pydantic Field() syntax for Pydantic 2 compatibility."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.results: list[FieldFixResult] = []

    def fix_file(self, file_path: Path) -> list[FieldFixResult]:
        """Fix Field() syntax in a single file."""
        if not file_path.exists():
            print(f"File not found: {file_path}")
            return []

        try:
            content = file_path.read_text()

            # First, fix multi-line Field() patterns
            fixed_content, multiline_results = self._fix_multiline_fields(
                content, str(file_path)
            )

            # Then fix single-line patterns
            lines = fixed_content.split("\n")
            fixed_lines = []
            results = multiline_results

            for line_num, line in enumerate(lines, start=1):
                fixed_line, result = self._fix_line(line, str(file_path), line_num)
                fixed_lines.append(fixed_line)

                if result:
                    results.append(result)
                    self.results.append(result)

            # Write back if not dry run and changes were made
            if results and not self.dry_run:
                new_content = "\n".join(fixed_lines)
                file_path.write_text(new_content)

            return results

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []

    def _fix_multiline_fields(
        self, content: str, file_path: str
    ) -> tuple[str, list[FieldFixResult]]:
        """Fix multi-line Field() definitions."""
        results = []

        # Pattern: Field(\n        None,\n        description=...)
        # Match Field with None as first positional arg (potentially multi-line)
        pattern = r"(\w+:\s*[^=]+\s*=\s*Field\s*\(\s*)None(\s*,)"

        def replacer(match):
            # Extract field name from the line before Field
            full_match = match.group(0)
            field_name = self._extract_field_name(full_match)

            # Count line number
            line_num = content[: match.start()].count("\n") + 1

            result = FieldFixResult(
                file_path=file_path,
                line_number=line_num,
                field_name=field_name,
                original_line=full_match,
                fixed_line=match.group(1) + "default=None" + match.group(2),
                fix_type="multiline_none_to_default",
                success=True,
            )
            results.append(result)
            self.results.append(result)

            return match.group(1) + "default=None" + match.group(2)

        fixed_content = re.sub(
            pattern, replacer, content, flags=re.MULTILINE | re.DOTALL
        )
        return fixed_content, results

    def _fix_line(
        self, line: str, file_path: str, line_number: int
    ) -> tuple[str, FieldFixResult | None]:
        """Fix a single line if it contains problematic Field() syntax."""
        # Skip if not a field definition
        if "Field(" not in line or "=" not in line:
            return line, None

        # Skip if it's a comment
        if line.strip().startswith("#"):
            return line, None

        # Skip if already using default= syntax
        if "Field(default=" in line or "Field(default_factory=" in line:
            return line, None

        # Skip if it's a required field (Field(...))
        if re.search(r"Field\s*\(\s*\.\.\.", line):
            return line, None

        # Pattern 1: Field(None, ...) -> Field(default=None, ...)
        pattern1 = r"(Field\s*\(\s*)None(\s*,)"
        match1 = re.search(pattern1, line)
        if match1:
            fixed_line = re.sub(pattern1, r"\1default=None\2", line)
            field_name = self._extract_field_name(line)
            return fixed_line, FieldFixResult(
                file_path=file_path,
                line_number=line_number,
                field_name=field_name,
                original_line=line,
                fixed_line=fixed_line,
                fix_type="none_to_default",
                success=True,
            )

        # Pattern 2: Field([]/{}/"", ...) -> Field(default=[]/{}/"", ...)
        # Match common default values
        default_values = [
            r"\[\]",  # Empty list
            r"\{\}",  # Empty dict
            r'""',  # Empty string
            r"''",  # Empty string
            r"0",  # Zero
            r"0\.0",  # Zero float
            r"False",  # Boolean
            r"True",  # Boolean
        ]

        for default_val in default_values:
            pattern = rf"(Field\s*\(\s*)({default_val})(\s*,)"
            match = re.search(pattern, line)
            if match:
                fixed_line = re.sub(pattern, r"\1default=\2\3", line)
                field_name = self._extract_field_name(line)
                return fixed_line, FieldFixResult(
                    file_path=file_path,
                    line_number=line_number,
                    field_name=field_name,
                    original_line=line,
                    fixed_line=fixed_line,
                    fix_type="value_to_default",
                    success=True,
                )

        return line, None

    def _extract_field_name(self, line: str) -> str:
        """Extract field name from a field definition line."""
        # Pattern: field_name: Type = Field(...)
        match = re.search(r"^\s*(\w+)\s*:", line)
        if match:
            return match.group(1)
        return "unknown"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fix Pydantic Field() syntax for Pydantic 2 compatibility"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Fix a specific file",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fix all model files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak backups before modifying files",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("src/omnibase_core/models"),
        help="Models directory to scan (default: src/omnibase_core/models)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.file and not args.all:
        parser.error("Must specify either --file or --all")

    # Collect files to process
    files_to_process = []

    if args.file:
        files_to_process = [args.file]
    elif args.all:
        if not args.models_dir.exists():
            print(f"Models directory not found: {args.models_dir}")
            return 1
        files_to_process = list(args.models_dir.rglob("*.py"))

    print(f"Processing {len(files_to_process)} files...")

    # Create fixer
    fixer = PydanticFieldSyntaxFixer(dry_run=args.dry_run)

    # Process files
    total_fixes = 0
    for file_path in files_to_process:
        # Create backup if requested
        if args.backup and not args.dry_run:
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy2(file_path, backup_path)

        # Fix the file
        results = fixer.fix_file(file_path)

        if results:
            total_fixes += len(results)
            print(f"\n{file_path.name}:")
            for result in results:
                print(f"  Line {result.line_number}: {result.field_name}")
                if args.dry_run:
                    print(f"    Before: {result.original_line.strip()}")
                    print(f"    After:  {result.fixed_line.strip()}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Files processed: {len(files_to_process)}")
    print(f"  Total fixes: {total_fixes}")

    if args.dry_run:
        print("\n  DRY RUN - No files were modified")
    else:
        print("\n  Files have been updated")

    # Breakdown by fix type
    if total_fixes > 0:
        fix_types = {}
        for result in fixer.results:
            fix_types[result.fix_type] = fix_types.get(result.fix_type, 0) + 1

        print("\n  Fix breakdown:")
        for fix_type, count in sorted(fix_types.items()):
            print(f"    {fix_type}: {count}")

    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
