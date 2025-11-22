#!/usr/bin/env python3
"""
Remove default_factory from version fields in subcontract models.

This script transforms:
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Model version",
    )

To:
    version: ModelSemVer = Field(
        description="Model version (MUST be provided in YAML contract)",
    )

This makes version a required field, enforcing that it must be provided in YAML contracts.
"""

import re
from pathlib import Path


def transform_version_field(content: str) -> tuple[str, int]:
    """
    Transform version field by removing default_factory.

    Returns:
        Tuple of (transformed_content, number_of_changes)
    """
    # Pattern to match the version field with default_factory
    pattern = r'(    version: ModelSemVer = Field\(\n)        default_factory=lambda: ModelSemVer\(major=1, minor=0, patch=0\),\n(        description="Model version",\n    \))'

    # Replacement - remove default_factory line and update description
    replacement = r'\1        description="Model version (MUST be provided in YAML contract)",\n    )'

    # Count matches before replacement
    matches = re.findall(pattern, content)
    count = len(matches)

    # Perform replacement
    transformed = re.sub(pattern, replacement, content)

    return transformed, count


def process_file(file_path: Path) -> tuple[bool, int]:
    """
    Process a single file.

    Returns:
        Tuple of (was_modified, number_of_changes)
    """
    try:
        # Read file
        content = file_path.read_text(encoding="utf-8")

        # Transform
        transformed, count = transform_version_field(content)

        if count > 0:
            # Write back
            file_path.write_text(transformed, encoding="utf-8")
            return True, count

        return False, 0

    except Exception as e:
        print(f"ERROR processing {file_path}: {e}")
        return False, 0


def main() -> None:
    """Main entry point."""
    # Base directory
    base_dir = (
        Path(__file__).parent.parent
        / "src"
        / "omnibase_core"
        / "models"
        / "contracts"
        / "subcontracts"
    )

    if not base_dir.exists():
        print(f"ERROR: Directory not found: {base_dir}")
        return

    # Find all Python files
    files = list(base_dir.glob("*.py"))

    print(f"Found {len(files)} files in {base_dir}")
    print()

    # Process files
    modified_files: list[tuple[Path, int]] = []
    total_changes = 0

    for file_path in sorted(files):
        was_modified, count = process_file(file_path)
        if was_modified:
            modified_files.append((file_path, count))
            total_changes += count
            print(f"✓ {file_path.name}: {count} change(s)")

    # Summary
    print()
    print("=" * 80)
    print(f"Modified {len(modified_files)} files")
    print(f"Total changes: {total_changes}")
    print("=" * 80)

    if modified_files:
        print("\nModified files:")
        for file_path, count in modified_files:
            print(f"  - {file_path.name} ({count} change(s))")


if __name__ == "__main__":
    main()
