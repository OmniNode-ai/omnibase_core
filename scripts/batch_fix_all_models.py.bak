#!/usr/bin/env python3
"""
Batch fix all model files - optimized version.
Processes multiple files without spawning subprocess for each.
"""

import sys
from pathlib import Path

# Import the fixer module
sys.path.insert(0, str(Path(__file__).parent))
from fix_string_versions_regex import fix_file


def main():
    """Process all model files efficiently."""
    project_root = Path(__file__).parent.parent

    # Find all model and mixin files
    model_files = list(project_root.glob("src/omnibase_core/models/**/*.py"))
    mixin_files = list(project_root.glob("src/omnibase_core/mixins/**/*.py"))
    all_files = model_files + mixin_files

    print(f"🔍 Found {len(all_files)} files to process")
    print("")

    fixed = 0
    skipped = 0
    errors = 0

    for i, filepath in enumerate(all_files, 1):
        filename = filepath.name
        print(f"[{i}/{len(all_files)}] {filename}...", end=" ", flush=True)

        try:
            success, message = fix_file(filepath, backup=True)
            if success:
                print("✅ Fixed")
                fixed += 1
            else:
                print("⏭️  No changes")
                skipped += 1
        except Exception as e:
            print(f"❌ Error: {e}")
            errors += 1

    print("")
    print("=" * 60)
    print("📈 Statistics:")
    print(f"   Total files:   {len(all_files)}")
    print(f"   Fixed:         {fixed}")
    print(f"   No changes:    {skipped}")
    print(f"   Errors:        {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
