#!/usr/bin/env python3
"""
Regex-based String Version Fixer for ONEX Compliance

Uses precise regex patterns to fix string version violations while
preserving original code formatting.
"""

import re
import sys
from pathlib import Path

# Field names that should use UUID
ID_FIELDS = {
    "run_id",
    "batch_id",
    "parent_id",
    "node_id",
    "service_id",
    "event_id",
    "pattern_id",
    "backend_id",
    "correlation_id",
    "task_id",
    "job_id",
    "session_id",
    "instance_id",
    "request_id",
    "response_id",
    "workflow_id",
    "execution_id",
    "transaction_id",
}

# Field names that should use ModelSemVer
VERSION_FIELDS = {
    "contract_version",
    "protocol_version",
    "version",
    "api_version",
    "schema_version",
}


def needs_uuid_import(content: str) -> bool:
    """Check if UUID import is needed."""
    # Check if UUID is already imported
    uuid_patterns = [
        r"from uuid import.*\bUUID\b",
        r"from uuid import UUID",
        r"import uuid",
    ]
    return not any(re.search(pattern, content) for pattern in uuid_patterns)


def needs_semver_import(content: str) -> bool:
    """Check if ModelSemVer import is needed."""
    # Check if ModelSemVer is already imported
    semver_patterns = [
        r"from omnibase_core\.models\.core\.model_semver import.*\bModelSemVer\b",
        r"from \.\.\.models\.core\.model_semver import.*\bModelSemVer\b",
        r"from \.model_semver import.*\bModelSemVer\b",
    ]
    return not any(re.search(pattern, content) for pattern in semver_patterns)


def add_imports(content: str, needs_uuid: bool, needs_semver: bool) -> str:
    """Add necessary imports to the file."""
    if not (needs_uuid or needs_semver):
        return content

    lines = content.split("\n")
    insert_pos = 0

    # Find the position to insert imports (after __future__ imports if present)
    for i, line in enumerate(lines):
        if line.startswith("from __future__") or (
            line.startswith(("import ", "from ")) and "import" in line
        ):
            insert_pos = i + 1
        elif line.strip() and not line.startswith("#"):
            # Stop at first non-import, non-comment line
            break

    # Prepare imports to add
    imports_to_add = []
    if needs_uuid:
        imports_to_add.append("from uuid import UUID")
    if needs_semver:
        imports_to_add.append(
            "from omnibase_core.models.core.model_semver import ModelSemVer"
        )

    # Insert imports
    for imp in reversed(imports_to_add):
        lines.insert(insert_pos, imp)

    return "\n".join(lines)


def fix_field_annotations(content: str) -> tuple[str, bool, bool]:
    """
    Fix field annotations using regex patterns.

    Returns:
        (fixed_content, needs_uuid, needs_semver)
    """
    needs_uuid = False
    needs_semver = False
    modified = content

    # Pattern 1: Fix ID fields in annotations
    # field_name: str | None = ... → field_name: UUID | None = ...
    # field_name: str = ... → field_name: UUID = ...
    for field in ID_FIELDS:
        # Pattern: field_name: str | None
        pattern = rf"(\b{field}\s*:\s*)str(\s*\|\s*None)"
        replacement = r"\1UUID\2"
        new_content = re.sub(pattern, replacement, modified)
        if new_content != modified:
            needs_uuid = True
            modified = new_content

        # Pattern: field_name: str (without None)
        pattern = rf"(\b{field}\s*:\s*)str(\s*=)"
        replacement = r"\1UUID\2"
        new_content = re.sub(pattern, replacement, modified)
        if new_content != modified:
            needs_uuid = True
            modified = new_content

    # Pattern 2: Fix version fields in annotations
    for field in VERSION_FIELDS:
        # Pattern: field_name: str | None
        pattern = rf"(\b{field}\s*:\s*)str(\s*\|\s*None)"
        replacement = r"\1ModelSemVer\2"
        new_content = re.sub(pattern, replacement, modified)
        if new_content != modified:
            needs_semver = True
            modified = new_content

        # Pattern: field_name: str (without None)
        pattern = rf"(\b{field}\s*:\s*)str(\s*=)"
        replacement = r"\1ModelSemVer\2"
        new_content = re.sub(pattern, replacement, modified)
        if new_content != modified:
            needs_semver = True
            modified = new_content

    return modified, needs_uuid, needs_semver


def fix_file(filepath: Path, backup: bool = True) -> tuple[bool, str]:
    """
    Fix string version violations in a file.

    Returns:
        (success, message) tuple
    """
    try:
        # Read original content
        content = filepath.read_text()
        original_content = content

        # Fix annotations
        content, needs_uuid, needs_semver = fix_field_annotations(content)

        # Add imports if needed
        if needs_uuid and needs_uuid_import(content):
            content = add_imports(content, True, False)

        if needs_semver and needs_semver_import(content):
            content = add_imports(content, False, True)

        # Only write if content changed
        if content != original_content:
            if backup:
                backup_path = filepath.with_suffix(filepath.suffix + ".bak")
                backup_path.write_text(original_content)
                print(f"  📝 Backed up to: {backup_path}")

            filepath.write_text(content)
            return True, "Fixed"
        else:
            return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python fix_string_versions_regex.py <file> [--backup]")
        print("\nExample:")
        print(
            "  python scripts/fix_string_versions_regex.py "
            "src/omnibase_core/models/core/model_contract_data.py --backup"
        )
        sys.exit(1)

    filepath = Path(sys.argv[1])
    backup = "--backup" in sys.argv

    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        sys.exit(1)

    print(f"🔧 Processing: {filepath}")
    success, message = fix_file(filepath, backup)

    if success:
        print(f"✅ {message}")
        sys.exit(0)
    else:
        print(f"⚠️  {message}")
        sys.exit(0 if message == "No changes needed" else 1)


if __name__ == "__main__":
    main()
