#!/usr/bin/env python3
"""
Fix Field() positional default arguments.

This script fixes the pattern:
    Field(value, description=..., ...)
To:
    Field(default=value, description=..., ...)

The positional syntax works at runtime but mypy doesn't recognize it.
"""

import re
import sys
from pathlib import Path


def fix_field_positional_defaults(content: str) -> tuple[str, int]:
    """
    Fix Field() calls with positional default values.

    Matches patterns like:
        Field(False, description="...")
        Field("value", description="...")
        Field(123, description="...", ge=0)

    And converts to:
        Field(default=False, description="...")
        Field(default="value", description="...")
        Field(default=123, description="...", ge=0)

    Returns:
        Tuple of (fixed_content, number_of_fixes)
    """
    fixes = 0

    # Pattern to match Field() calls with positional default
    # This matches: Field(value, keyword_arg=...)
    # Where value can be:
    # - None
    # - True/False
    # - Numbers (int/float)
    # - Strings (single or double quoted)
    # - Lists/sets/dicts (basic)
    # - Lambda functions
    # - factory functions

    pattern = r'Field\(\s*([^,\s=][^,=]*?)\s*,\s+([a-z_]+\s*=)'

    def replace_func(match):
        nonlocal fixes
        value = match.group(1).strip()
        first_kwarg = match.group(2)

        # Don't replace if value already looks like a keyword argument
        if '=' in value:
            return match.group(0)

        # Don't replace if value is 'default='
        if value == 'default':
            return match.group(0)

        fixes += 1
        return f'Field(default={value}, {first_kwarg}'

    fixed_content = re.sub(pattern, replace_func, content)

    return fixed_content, fixes


def process_file(file_path: Path) -> bool:
    """Process a single Python file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        fixed_content, fixes = fix_field_positional_defaults(content)

        if fixes > 0:
            file_path.write_text(fixed_content, encoding='utf-8')
            print(f"✓ {file_path}: {fixes} fixes")
            return True

        return False
    except Exception as e:
        print(f"✗ {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    src_dir = Path(__file__).parent.parent / "src" / "omnibase_core"

    if not src_dir.exists():
        print(f"Error: {src_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all Python files
    py_files = list(src_dir.rglob("*.py"))

    print(f"Processing {len(py_files)} Python files...")

    fixed_files = 0
    for py_file in py_files:
        if process_file(py_file):
            fixed_files += 1

    print(f"\nFixed {fixed_files} files")


if __name__ == "__main__":
    main()
