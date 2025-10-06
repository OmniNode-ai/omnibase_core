#!/usr/bin/env python3
"""Fix syntax errors caused by incorrect import placement."""

import re
import subprocess
from pathlib import Path


def find_files_with_syntax_errors():
    """Find all files with syntax errors from mypy."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/"],
        capture_output=True,
        text=True,
        cwd="/Volumes/PRO-G40/Code/omnibase_core"
    )
    output = result.stdout + result.stderr

    files = []
    for line in output.split('\n'):
        if 'Invalid syntax' in line:
            match = re.match(r'^(.+?):\d+:', line)
            if match:
                files.append(match.group(1))

    return files


def fix_file(file_path):
    """Fix import syntax errors in a file."""
    path = Path(file_path)
    if not path.exists():
        return False

    content = path.read_text()
    original = content

    # Pattern: multi-line import with error_codes import in the middle
    # from X import (
    # from omnibase_core.errors.error_codes import ModelCoreErrorCode
    #     Y,
    # )
    pattern = r'(from\s+\S+\s+import\s+\(\s*\n)(from omnibase_core\.errors\.error_codes import ModelCoreErrorCode\s*\n)(\s+[^)]+\))'

    def replacement(match):
        """Move the error_codes import after the closing paren."""
        return match.group(1) + match.group(3) + '\nfrom omnibase_core.errors.error_codes import ModelCoreErrorCode'

    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    if content != original:
        path.write_text(content)
        return True

    return False


def main():
    """Main function."""
    print("Finding files with syntax errors...")
    files = find_files_with_syntax_errors()

    if not files:
        print("No syntax errors found!")
        return

    print(f"Found {len(files)} files with syntax errors")

    fixed = 0
    for file_path in files:
        if fix_file(file_path):
            print(f"  ✓ Fixed: {file_path}")
            fixed += 1
        else:
            print(f"  - No fix applied: {file_path}")

    print(f"\nFixed {fixed} files")


if __name__ == '__main__':
    main()
