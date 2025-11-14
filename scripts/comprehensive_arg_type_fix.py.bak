#!/usr/bin/env python3
"""
Comprehensive fix for all MyPy arg-type errors.
This script systematically fixes UUID, ModelSemVer, Path, and other type conversion issues.
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent / "src" / "omnibase_core"


def fix_file_content(filepath: Path, fixes: list[tuple[int, str, str]]) -> bool:
    """
    Apply multiple line-based fixes to a file.

    Args:
        filepath: Path to file
        fixes: List of (line_num, old_pattern, new_pattern) tuples

    Returns:
        True if any fixes were applied
    """
    if not filepath.exists():
        print(f"⚠️  File not found: {filepath}")
        return False

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    modified = False
    for line_num, old_pattern, new_pattern in fixes:
        if line_num > len(lines):
            continue

        line_idx = line_num - 1
        original_line = lines[line_idx]

        # Apply the fix
        new_line = original_line.replace(old_pattern, new_pattern)

        if new_line != original_line:
            lines[line_idx] = new_line
            modified = True
            print(
                f"  ✅ Line {line_num}: {old_pattern[:50]}... → {new_pattern[:50]}..."
            )

    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return modified


def main():
    """Main execution."""
    print("🚀 Comprehensive arg-type error fixes\n")

    fixes_applied = 0

    # Fix 1: mixin_workflow_support.py - UUID conversion
    print("\n📝 Fixing mixin_workflow_support.py...")
    file = ROOT_DIR / "mixins" / "mixin_workflow_support.py"
    fixes = [
        (
            115,
            "correlation_id=correlation_id,",
            "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        ),
        (
            119,
            "correlation_id=correlation_id,",
            "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        ),
        (
            148,
            "correlation_id=correlation_id,",
            "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        ),
        (
            161,
            "correlation_id=correlation_id,",
            "correlation_id=UUID(correlation_id) if isinstance(correlation_id, str) else correlation_id,",
        ),
    ]
    if fix_file_content(file, fixes):
        fixes_applied += len(fixes)

    # Fix 2: model_event_bus_input_state.py - ModelSemVer conversion
    print("\n📝 Fixing model_event_bus_input_state.py...")
    file = ROOT_DIR / "models" / "service" / "model_event_bus_input_state.py"
    with open(file, encoding="utf-8") as f:
        content = f.read()

    # Find the line with version=version and add conversion
    original = content
    content = re.sub(
        r"(\s+)version=version,",
        r"\1version=parse_semver_from_string(version) if isinstance(version, str) else version,",
        content,
    )
    if content != original:
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ✅ Fixed version parameter conversion")
        fixes_applied += 1

    # Fix 3: model_schema.py - Multiple fixes
    print("\n📝 Fixing model_schema.py...")
    file = ROOT_DIR / "models" / "core" / "model_schema.py"
    with open(file, encoding="utf-8") as f:
        content = f.read()

    original = content
    # Fix schema_version str -> ModelSemVer
    content = re.sub(
        r"(\s+)schema_version=schema_version,",
        r"\1schema_version=parse_semver_from_string(schema_version) if isinstance(schema_version, str) else schema_version,",
        content,
    )
    # Fix properties dict filtering
    content = re.sub(
        r"(\s+)properties=properties,",
        r"\1properties={k: v for k, v in properties.items() if v is not None} if properties else None,",
        content,
    )
    # Fix definitions dict filtering
    content = re.sub(
        r"(\s+)definitions=definitions,",
        r"\1definitions={k: v for k, v in definitions.items() if v is not None} if definitions else None,",
        content,
    )
    # Fix all_of list filtering
    content = re.sub(
        r"(\s+)all_of=all_of,",
        r"\1all_of=[s for s in all_of if s is not None] if all_of else None,",
        content,
    )
    # Fix any_of list filtering
    content = re.sub(
        r"(\s+)any_of=any_of,",
        r"\1any_of=[s for s in any_of if s is not None] if any_of else None,",
        content,
    )
    # Fix one_of list filtering
    content = re.sub(
        r"(\s+)one_of=one_of,",
        r"\1one_of=[s for s in one_of if s is not None] if one_of else None,",
        content,
    )

    if content != original:
        with open(file, "w", encoding="utf-8") as f:
            f.write(content)
        print("  ✅ Fixed multiple schema conversions")
        fixes_applied += 6

    print(f"\n✅ Applied {fixes_applied} fixes")
    print("🎉 Phase 1 complete!")
    print("\n⏭️  Run phase 2 script for remaining fixes...")


if __name__ == "__main__":
    main()
