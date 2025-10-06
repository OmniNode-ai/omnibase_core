#!/usr/bin/env python3
"""
Find and fix syntax errors blocking MyPy.
"""
import re
import subprocess
from pathlib import Path

ROOT_DIR = Path("/Volumes/PRO-G40/Code/omnibase_core")


def run_mypy() -> tuple[bool, str, str]:
    """Run MyPy and return (has_syntax_error, filepath, line)."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
    )
    output = result.stdout + result.stderr

    # Check for syntax errors
    match = re.search(r'(src/omnibase_core/[^:]+):(\d+): error: Invalid syntax', output)
    if match:
        return True, match.group(1), match.group(2)

    return False, "", ""


def fix_common_syntax_errors(filepath: str, line_num: int) -> bool:
    """Fix common syntax error patterns."""
    path = Path(filepath)
    if not path.exists():
        return False

    content = path.read_text()
    lines = content.split('\n')
    line_idx = line_num - 1

    if line_idx >= len(lines):
        return False

    line = lines[line_idx]
    original_line = line

    # Pattern 1: `from typing import (, Any` -> remove empty parens
    if re.search(r'from\s+\w+\s+import\s+\(,', line):
        line = re.sub(r'\(,\s*', '(', line)
        print(f"  Fixed: Removed empty tuple in import")

    # Pattern 2: Misplaced import inside another import
    # Check if this line has an import inside parentheses
    if line.strip().startswith('from ') and '(' not in line:
        # Check next few lines for misplaced imports
        for i in range(line_idx + 1, min(line_idx + 5, len(lines))):
            if lines[i].strip().startswith('from ') and not lines[i].strip().endswith(')'):
                # This is a misplaced import - remove it
                print(f"  Fixed: Removed misplaced import on line {i+1}: {lines[i].strip()}")
                lines[i] = ''
                path.write_text('\n'.join(lines))
                return True

    # Pattern 3: from omnibase_core.enums.enum_status_migration import EnumStatusMigrationValidator
    # Check if line contains misplaced 'from' statements
    if 'from omnibase_core.enums.enum_status_migration import EnumStatusMigrationValidator' in line:
        # This import might be in the wrong place - check context
        if line_idx > 0 and 'import' in lines[line_idx - 1]:
            # Remove this duplicate/misplaced import
            print(f"  Fixed: Removed duplicate import on line {line_num}")
            lines[line_idx] = ''
            path.write_text('\n'.join(lines))
            return True

    # If line changed, save it
    if line != original_line:
        lines[line_idx] = line
        path.write_text('\n'.join(lines))
        return True

    # Manual inspection needed
    print(f"  Could not auto-fix. Line {line_num}:")
    print(f"    {line}")
    return False


def main():
    """Main execution."""
    print("=" * 80)
    print("Fix Syntax Errors Blocking MyPy")
    print("=" * 80)

    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        has_error, filepath, line_num = run_mypy()

        if not has_error:
            print("\n✓ No more syntax errors found!")
            break

        iteration += 1
        print(f"\nIteration {iteration}: Syntax error in {Path(filepath).name}:{line_num}")

        fixed = fix_common_syntax_errors(filepath, int(line_num))

        if not fixed:
            print(f"\n✗ Could not auto-fix. Manual intervention required.")
            print(f"  File: {filepath}")
            print(f"  Line: {line_num}")
            break

    print("\n" + "=" * 80)
    print("Done")
    print("=" * 80)


if __name__ == '__main__':
    main()
