#!/usr/bin/env python3
"""Remove default_factory from version fields - make versions required.

This script transforms:
    version: ModelSemVer | None = Field(
        default_factory=default_model_version,
        description="...",
    )

To:
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="...",
    )

Also handles lambda patterns and removes unused imports.
Handles all version-related fields: version, node_version, workflow_version,
schema_version, blueprint_version, etc.
"""

import argparse
import re
import sys
from pathlib import Path

# All version-related field names to target (match any field ending in _version or just version)
VERSION_FIELDS = r"(?:\w*_?version)"

# Type names that could be used for versions
VERSION_TYPES = r"(?:ModelSemVer|SemVerField)"


def fix_file(filepath: Path, verbose: bool = False) -> int:
    """Fix a single file. Returns number of fixes made."""
    content = filepath.read_text(encoding="utf-8")
    original_content = content
    fixes = 0

    # Pattern 1: default_factory=default_model_version (multi-line)
    # Matches any version field with default_factory=default_model_version
    pattern1 = re.compile(
        r"(\s+)("
        + VERSION_FIELDS
        + r"): ("
        + VERSION_TYPES
        + r")( \| None)? = Field\(\s*\n"
        r"\s+default_factory=default_model_version,\s*\n"
        r"(\s+description=)",
        re.MULTILINE,
    )

    def replace1(match: re.Match[str]) -> str:
        nonlocal fixes
        indent = match.group(1)
        field_name = match.group(2)
        type_name = match.group(3)
        desc_part = match.group(5)
        fixes += 1
        return (
            f"{indent}{field_name}: {type_name} = Field(\n"
            f"{indent}    ...,  # REQUIRED - specify in contract\n"
            f"{desc_part}"
        )

    content = pattern1.sub(replace1, content)

    # Pattern 2: default_factory=default_model_version (single line or variant)
    pattern2 = re.compile(
        r"(\s+)(" + VERSION_FIELDS + r"): (" + VERSION_TYPES + r")( \| None)? = Field\("
        r"default_factory=default_model_version,",
        re.MULTILINE,
    )

    def replace2(match: re.Match[str]) -> str:
        nonlocal fixes
        indent = match.group(1)
        field_name = match.group(2)
        type_name = match.group(3)
        fixes += 1
        return (
            f"{indent}{field_name}: {type_name} = Field(\n"
            f"{indent}    ...,  # REQUIRED - specify in contract\n"
            f"{indent}   "
        )

    content = pattern2.sub(replace2, content)

    # Pattern 3: default_factory=lambda: ModelSemVer(...) - multi-line
    pattern3 = re.compile(
        r"(\s+)("
        + VERSION_FIELDS
        + r"): ("
        + VERSION_TYPES
        + r")( \| None)? = Field\(\s*\n"
        r"\s+default_factory=lambda: ModelSemVer\([^)]+\),\s*\n"
        r"(\s+description=)",
        re.MULTILINE,
    )

    def replace3(match: re.Match[str]) -> str:
        nonlocal fixes
        indent = match.group(1)
        field_name = match.group(2)
        type_name = match.group(3)
        desc_part = match.group(5)
        fixes += 1
        return (
            f"{indent}{field_name}: {type_name} = Field(\n"
            f"{indent}    ...,  # REQUIRED - specify in contract\n"
            f"{desc_part}"
        )

    content = pattern3.sub(replace3, content)

    # Pattern 4: default_factory=lambda: ModelSemVer(...) - single line style
    pattern4 = re.compile(
        r"(\s+)(" + VERSION_FIELDS + r"): (" + VERSION_TYPES + r")( \| None)? = Field\("
        r"default_factory=lambda: ModelSemVer\([^)]+\),",
        re.MULTILINE,
    )

    def replace4(match: re.Match[str]) -> str:
        nonlocal fixes
        indent = match.group(1)
        field_name = match.group(2)
        type_name = match.group(3)
        fixes += 1
        return (
            f"{indent}{field_name}: {type_name} = Field(\n"
            f"{indent}    ...,  # REQUIRED - specify in contract\n"
            f"{indent}   "
        )

    content = pattern4.sub(replace4, content)

    # After all fixes, check if default_model_version is still used
    if fixes > 0 and "default_model_version" not in content.replace(
        "from omnibase_core.models.primitives.model_semver import", ""
    ).replace("import default_model_version", ""):
        # Remove the import - various patterns

        # Multi-line import with both (multiple items)
        content = re.sub(
            r"from omnibase_core\.models\.primitives\.model_semver import \(\s*\n"
            r"\s+ModelSemVer,\s*\n"
            r"\s+default_model_version,\s*\n"
            r"\)",
            "from omnibase_core.models.primitives.model_semver import ModelSemVer",
            content,
        )

        # Reverse order
        content = re.sub(
            r"from omnibase_core\.models\.primitives\.model_semver import \(\s*\n"
            r"\s+default_model_version,\s*\n"
            r"\s+ModelSemVer,\s*\n"
            r"\)",
            "from omnibase_core.models.primitives.model_semver import ModelSemVer",
            content,
        )

        # Single line with both
        content = re.sub(
            r"from omnibase_core\.models\.primitives\.model_semver import ModelSemVer, default_model_version",
            "from omnibase_core.models.primitives.model_semver import ModelSemVer",
            content,
        )
        content = re.sub(
            r"from omnibase_core\.models\.primitives\.model_semver import default_model_version, ModelSemVer",
            "from omnibase_core.models.primitives.model_semver import ModelSemVer",
            content,
        )

        # Just default_model_version alone (remove entire import)
        content = re.sub(
            r"from omnibase_core\.models\.primitives\.model_semver import default_model_version\n",
            "",
            content,
        )

        # Clean up comma in multi-import when default_model_version is removed from middle/end
        # e.g., "ModelSemVer,\n    default_model_version," -> "ModelSemVer,"
        content = re.sub(
            r"(\bModelSemVer\b),\s*\n\s*default_model_version,?",
            r"\1,",
            content,
        )

    if content != original_content:
        filepath.write_text(content, encoding="utf-8")

    return fixes


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Remove default_factory from version fields - make versions required"
    )
    parser.add_argument(
        "directories",
        nargs="*",
        type=Path,
        help="Directories to scan (default: contracts and core)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = (
        script_dir.parent.parent
    )  # scripts/migration -> scripts -> project root

    # Default directories
    if not args.directories:
        base = project_root / "src" / "omnibase_core" / "models"
        directories = [
            base / "contracts",
            base / "core",
        ]
    else:
        directories = args.directories

    total_fixes = 0
    files_fixed = 0

    for directory in directories:
        if not directory.exists():
            print(f"Warning: Directory does not exist: {directory}")
            continue

        print(f"\nScanning: {directory}")
        for filepath in sorted(directory.rglob("*.py")):
            try:
                content = filepath.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                print(f"  Error reading {filepath}: {e}")
                continue

            # Check if file has patterns we're looking for
            if "default_factory=default_model_version" in content or (
                "default_factory=lambda" in content and "ModelSemVer" in content
            ):
                if args.dry_run:
                    print(f"  Would fix: {filepath.name}")
                    continue

                fixes = fix_file(filepath, verbose=args.verbose)
                if fixes > 0:
                    rel_path = filepath.relative_to(project_root)
                    print(f"  Fixed: {rel_path} ({fixes} change(s))")
                    total_fixes += fixes
                    files_fixed += 1

    print(
        f"\n{'Would fix' if args.dry_run else 'Fixed'}: {total_fixes} version fields in {files_fixed} files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
