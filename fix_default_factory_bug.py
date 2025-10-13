#!/usr/bin/env python3
"""
Fix CRITICAL BUG: default_factory with type annotations

PROBLEM:
  Field(default_factory=dict[str, Any])  # ❌ WRONG - dict[str, Any] is not callable!
  Field(default_factory=list[Any])       # ❌ WRONG - list[Any] is not callable!

SOLUTION:
  Field(default_factory=dict)            # ✅ CORRECT - dict is callable
  Field(default_factory=list)            # ✅ CORRECT - list is callable

The type annotation goes on the FIELD, not in default_factory:
  metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)  # ✅ CORRECT
"""

import re
import sys
from pathlib import Path


def fix_file(file_path: Path) -> tuple[bool, int]:
    """
    Fix default_factory bugs in a single file.

    Returns:
        (changed, count) - Whether file was modified and number of fixes
    """
    content = file_path.read_text()
    original_content = content
    fix_count = 0

    # Pattern 1: default_factory=dict[str, Any] → default_factory=dict
    pattern1 = r"default_factory=dict\[str,\s*Any\]"
    matches1 = len(re.findall(pattern1, content))
    content = re.sub(pattern1, "default_factory=dict", content)
    fix_count += matches1

    # Pattern 2: default_factory=list[Any] → default_factory=list
    pattern2 = r"default_factory=list\[Any\]"
    matches2 = len(re.findall(pattern2, content))
    content = re.sub(pattern2, "default_factory=list", content)
    fix_count += matches2

    # Pattern 3: default_factory=dict[str, <other types>] → default_factory=dict
    # Examples: dict[str, str], dict[str, int], dict[str, float], etc.
    pattern3 = r"default_factory=dict\[[^\]]+\]"
    matches3 = len(re.findall(pattern3, content))
    content = re.sub(pattern3, "default_factory=dict", content)
    fix_count += matches3

    # Pattern 4: default_factory=list[<type>] → default_factory=list
    # Examples: list[str], list[int], etc.
    pattern4 = r"default_factory=list\[[^\]]+\]"
    # Subtract already counted list[Any] to avoid double counting
    matches4 = len(re.findall(pattern4, content)) - matches2
    content = re.sub(pattern4, "default_factory=list", content)
    fix_count += matches4

    changed = content != original_content

    if changed:
        file_path.write_text(content)
        print(f"✅ Fixed {fix_count} issues in {file_path}")

    return changed, fix_count


def main():
    """Fix all files in the codebase."""
    src_path = Path("/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core")

    if not src_path.exists():
        print(f"❌ Error: {src_path} does not exist")
        sys.exit(1)

    # Find all Python files
    python_files = list(src_path.rglob("*.py"))

    print(f"🔍 Scanning {len(python_files)} Python files...")
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
    print("📊 SUMMARY:")
    print(f"   Files scanned: {len(python_files)}")
    print(f"   Files changed: {total_files_changed}")
    print(f"   Total fixes:   {total_fixes}")
    print()

    if total_fixes > 0:
        print("✅ All default_factory bugs have been fixed!")
        print()
        print("WHAT WAS FIXED:")
        print("   default_factory=dict[str, Any]  → default_factory=dict")
        print("   default_factory=list[Any]       → default_factory=list")
        print("   default_factory=dict[str, X]    → default_factory=dict")
        print("   default_factory=list[X]         → default_factory=list")
        print()
        print("WHY THIS MATTERS:")
        print("   - default_factory expects a CALLABLE (function)")
        print("   - dict[str, Any] is a TYPE ANNOTATION, not a callable")
        print("   - The type annotation belongs on the field itself")
        print("   - Example: metadata: dict[str, Any] = Field(default_factory=dict)")
    else:
        print("✅ No default_factory bugs found!")

    print("=" * 80)


if __name__ == "__main__":
    main()
