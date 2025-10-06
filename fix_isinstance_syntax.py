#!/usr/bin/env python3
"""
Fix isinstance syntax errors where closing brackets were lost.

PROBLEM: isinstance(x, dict[str, Any) → isinstance(x, dict)
         missing closing bracket!

SOLUTION: isinstance(x, dict) with proper closing parenthesis
"""

import re
import sys
from pathlib import Path


def fix_isinstance_syntax(content: str) -> tuple[str, int]:
    """Fix isinstance checks with missing closing brackets."""
    count = 0

    # Pattern 1: isinstance(x, dict[str, Any) → isinstance(x, dict)
    pattern1 = r"isinstance\s*\([^,]+,\s*dict\[str,\s*Any\)"
    matches1 = len(re.findall(pattern1, content))
    content = re.sub(
        pattern1, lambda m: m.group().replace("dict[str, Any)", "dict)"), content
    )
    count += matches1

    # Pattern 2: isinstance(x, list[Any) → isinstance(x, list)
    pattern2 = r"isinstance\s*\([^,]+,\s*list\[Any\)"
    matches2 = len(re.findall(pattern2, content))
    content = re.sub(
        pattern2, lambda m: m.group().replace("list[Any)", "list)"), content
    )
    count += matches2

    # Pattern 3: Check for any remaining generic types in isinstance
    pattern3 = r"isinstance\s*\([^,]+,\s*\w+\[[^\]]+\][^\)]*\)"
    matches3 = re.findall(pattern3, content)
    for match in matches3:
        # Skip if it's already been fixed
        if "dict)" in match or "list)" in match:
            continue
        # Remove all generic annotations
        fixed = re.sub(r"(\w+)\[[^\]]+\]", r"\1", match)
        if fixed != match:
            content = content.replace(match, fixed)
            count += 1

    return content, count


def fix_file(file_path: Path) -> tuple[bool, int]:
    """Fix isinstance syntax errors in a file."""
    try:
        content = file_path.read_text()
        original_content = content

        content, count = fix_isinstance_syntax(content)

        changed = content != original_content

        if changed:
            file_path.write_text(content)
            print(f"✅ Fixed {count} isinstance syntax errors in {file_path}")

        return changed, count
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False, 0


def main():
    """Fix all files in the codebase."""
    src_path = Path("/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core")

    if not src_path.exists():
        print(f"❌ Error: {src_path} does not exist")
        sys.exit(1)

    python_files = list(src_path.rglob("*.py"))

    print(
        f"🔍 Scanning {len(python_files)} Python files for isinstance syntax errors..."
    )
    print()

    total_files_changed = 0
    total_fixes = 0

    for file_path in python_files:
        changed, count = fix_file(file_path)
        if changed:
            total_files_changed += 1
            total_fixes += count

    print()
    print("=" * 80)
    print(f"📊 SUMMARY:")
    print(f"   Files scanned:  {len(python_files)}")
    print(f"   Files changed:  {total_files_changed}")
    print(f"   Total fixes:    {total_fixes}")
    print()

    if total_fixes > 0:
        print("✅ All isinstance syntax errors fixed!")
        print()
        print("WHAT WAS FIXED:")
        print("   isinstance(x, dict[str, Any)  → isinstance(x, dict)")
        print("   isinstance(x, list[Any)       → isinstance(x, list)")
    else:
        print("✅ No isinstance syntax errors found!")

    print("=" * 80)


if __name__ == "__main__":
    main()
