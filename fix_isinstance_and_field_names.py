#!/usr/bin/env python3
"""
Fix isinstance checks with generic types and restore field names.

CRITICAL FIXES:
1. isinstance(x, dict[str, Any]) → isinstance(x, dict)
2. isinstance(x, list[Any]) → isinstance(x, list)
3. list[Any]_field_name → list_field_name
4. dict[str, Any]_field_name → dict_field_name
"""

import re
import sys
from pathlib import Path


def fix_isinstance_checks(content: str) -> tuple[str, int]:
    """Fix isinstance checks that use generic types."""
    count = 0

    # Pattern: isinstance(x, dict[...])
    pattern1 = r"isinstance\s*\([^,]+,\s*dict\[[^\]]+\]\s*\)"
    matches1 = re.findall(pattern1, content)
    count += len(matches1)
    content = re.sub(
        pattern1,
        lambda m: m.group()
        .replace("dict[", "dict_PLACEHOLDER[")
        .replace("])", ")")
        .replace("dict_PLACEHOLDER", "dict"),
        content,
    )

    # Pattern: isinstance(x, list[...])
    pattern2 = r"isinstance\s*\([^,]+,\s*list\[[^\]]+\]\s*\)"
    matches2 = re.findall(pattern2, content)
    count += len(matches2)
    content = re.sub(
        pattern2,
        lambda m: m.group()
        .replace("list[", "list_PLACEHOLDER[")
        .replace("])", ")")
        .replace("list_PLACEHOLDER", "list"),
        content,
    )

    # Pattern: isinstance(x, (tuple, including, dict[...]))
    pattern3 = r"isinstance\s*\([^,]+,\s*\([^)]*dict\[[^\]]+\][^)]*\)\s*\)"
    matches3 = re.findall(pattern3, content)
    for match in matches3:
        fixed = match
        # Remove all dict[...] and list[...] generic annotations
        fixed = re.sub(r"dict\[[^\]]+\]", "dict", fixed)
        fixed = re.sub(r"list\[[^\]]+\]", "list", fixed)
        if fixed != match:
            content = content.replace(match, fixed)
            count += 1

    # Pattern: isinstance(x, (tuple, including, list[...]))
    pattern4 = r"isinstance\s*\([^,]+,\s*\([^)]*list\[[^\]]+\][^)]*\)\s*\)"
    matches4 = re.findall(pattern4, content)
    for match in matches4:
        fixed = match
        fixed = re.sub(r"list\[[^\]]+\]", "list", fixed)
        fixed = re.sub(r"dict\[[^\]]+\]", "dict", fixed)
        if fixed != match:
            content = content.replace(match, fixed)
            count += 1

    return content, count


def fix_field_names(content: str) -> tuple[str, int]:
    """Fix field names that were incorrectly modified by the previous script."""
    count = 0

    # Pattern: list[Any]_something (field name)
    # This should be list_something
    pattern1 = r"\blist\[Any\]_(\w+)"
    matches1 = len(re.findall(pattern1, content))
    content = re.sub(pattern1, r"list_\1", content)
    count += matches1

    # Pattern: dict[str, Any]_something (field name)
    # This should be dict_something
    pattern2 = r"\bdict\[str,\s*Any\]_(\w+)"
    matches2 = len(re.findall(pattern2, content))
    content = re.sub(pattern2, r"dict_\1", content)
    count += matches2

    # Also fix in strings (for validator names, etc)
    pattern3 = r'"list\[Any\]_(\w+)"'
    matches3 = len(re.findall(pattern3, content))
    content = re.sub(pattern3, r'"list_\1"', content)
    count += matches3

    pattern4 = r'"dict\[str,\s*Any\]_(\w+)"'
    matches4 = len(re.findall(pattern4, content))
    content = re.sub(pattern4, r'"dict_\1"', content)
    count += matches4

    # Fix enum values
    pattern5 = r'= "list\[Any\]_(\w+)"'
    matches5 = len(re.findall(pattern5, content))
    content = re.sub(pattern5, r'= "list_\1"', content)
    count += matches5

    pattern6 = r'= "dict\[str,\s*Any\]_(\w+)"'
    matches6 = len(re.findall(pattern6, content))
    content = re.sub(pattern6, r'= "dict_\1"', content)
    count += matches6

    return content, count


def fix_file(file_path: Path) -> tuple[bool, int, int]:
    """
    Fix both isinstance checks and field names in a file.

    Returns:
        (changed, isinstance_fixes, field_name_fixes)
    """
    content = file_path.read_text()
    original_content = content

    # Fix isinstance checks
    content, isinstance_count = fix_isinstance_checks(content)

    # Fix field names
    content, field_name_count = fix_field_names(content)

    total_fixes = isinstance_count + field_name_count
    changed = content != original_content

    if changed:
        file_path.write_text(content)
        if isinstance_count > 0 or field_name_count > 0:
            print(f"✅ Fixed {file_path}")
            if isinstance_count > 0:
                print(f"   - {isinstance_count} isinstance checks")
            if field_name_count > 0:
                print(f"   - {field_name_count} field name fixes")

    return changed, isinstance_count, field_name_count


def main():
    """Fix all files in the codebase."""
    src_path = Path("/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core")

    if not src_path.exists():
        print(f"❌ Error: {src_path} does not exist")
        sys.exit(1)

    python_files = list(src_path.rglob("*.py"))

    print(f"🔍 Scanning {len(python_files)} Python files...")
    print()

    total_files_changed = 0
    total_isinstance_fixes = 0
    total_field_name_fixes = 0

    for file_path in python_files:
        changed, isinstance_count, field_name_count = fix_file(file_path)
        if changed:
            total_files_changed += 1
            total_isinstance_fixes += isinstance_count
            total_field_name_fixes += field_name_count

    print()
    print("=" * 80)
    print("📊 SUMMARY:")
    print(f"   Files scanned:        {len(python_files)}")
    print(f"   Files changed:        {total_files_changed}")
    print(f"   isinstance fixes:     {total_isinstance_fixes}")
    print(f"   Field name fixes:     {total_field_name_fixes}")
    print(f"   Total fixes:          {total_isinstance_fixes + total_field_name_fixes}")
    print()

    if total_isinstance_fixes + total_field_name_fixes > 0:
        print("✅ All fixes applied!")
        print()
        print("WHAT WAS FIXED:")
        print("   isinstance(x, dict[str, Any])  → isinstance(x, dict)")
        print("   isinstance(x, list[Any])       → isinstance(x, list)")
        print("   list[Any]_field_name           → list_field_name")
        print("   dict[str, Any]_field_name      → dict_field_name")
    else:
        print("✅ No issues found!")

    print("=" * 80)


if __name__ == "__main__":
    main()
