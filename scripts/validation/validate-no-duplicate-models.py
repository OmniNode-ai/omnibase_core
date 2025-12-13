#!/usr/bin/env python3
"""
Prevent duplicate model filenames across directories.

This script ensures that no two model files have the same filename,
even if they're in different directories. This prevents namespace
collisions and import confusion.

Exit codes:
    0: No duplicates found
    1: Duplicates found
"""

import sys
from collections import defaultdict
from pathlib import Path


def find_duplicate_filenames(src_dir: Path) -> dict[str, list[Path]]:
    """Find all duplicate model filenames.

    Args:
        src_dir: Directory to search for model files

    Returns:
        Dict mapping filename to list of paths where it appears
    """
    # Known legacy duplicates that will be resolved in separate PRs
    # These are pre-existing issues tracked for future cleanup
    legacy_duplicates = {
        "model_service_registry_config.py",  # core vs service versions
    }

    files_by_name = defaultdict(list)

    for file_path in src_dir.rglob("model_*.py"):
        if "__pycache__" not in str(file_path):
            if file_path.name not in legacy_duplicates:
                files_by_name[file_path.name].append(file_path)

    # Return only duplicates
    return {name: paths for name, paths in files_by_name.items() if len(paths) > 1}


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = duplicates found)
    """
    src_dir = Path("src/omnibase_core/models")

    if not src_dir.exists():
        print(f"❌ Error: {src_dir} does not exist")
        return 1

    duplicates = find_duplicate_filenames(src_dir)

    if duplicates:
        print("❌ Duplicate model filenames found:")
        print()
        for filename, paths in sorted(duplicates.items()):
            print(f"  {filename} ({len(paths)} copies):")
            for path in sorted(paths):
                relative_path = path.relative_to(Path("src"))
                print(f"    - {relative_path}")

        print()
        print("💡 To fix:")
        print("  1. Consolidate identical files (keep one, delete others)")
        print("  2. Rename files with domain prefix (model_domain_name.py)")
        print("  3. Use more specific names to differentiate purposes")
        print()
        print("See: DUPLICATE_MODELS_RESOLUTION_PLAN.md for guidelines")

        return 1

    print("✅ No duplicate model filenames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
