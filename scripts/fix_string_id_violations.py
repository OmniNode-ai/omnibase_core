#!/usr/bin/env python3
"""
Fix string ID and version anti-patterns in model files.

Transforms:
1. ID fields: str -> UUID
   - field_id: str -> field_id: UUID
   - default_factory=lambda: str(uuid4()) -> default_factory=uuid4

2. Version fields: str -> ModelSemVer
   - version: str -> version: ModelSemVer
   - default="1.0.0" -> default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0)
"""

import re
import sys
from pathlib import Path


def fix_id_field_simple(content: str, field_name: str) -> str:
    """Fix simple ID field: field_name: str -> field_name: UUID"""
    # Match: field_name: str = Field(...)
    pattern = rf"(\s+{field_name}:\s+)str(\s*=\s*Field\()"
    replacement = r"\1UUID\2"
    return re.sub(pattern, replacement, content)


def fix_id_field_with_uuid_factory(content: str) -> str:
    """Fix ID fields with str(uuid4()) factory -> uuid4"""
    # Match: default_factory=lambda: str(uuid4())
    pattern = r"default_factory=lambda:\s*str\(uuid4\(\)\)"
    replacement = "default_factory=uuid4"
    return re.sub(pattern, replacement, content)


def fix_version_field_simple(
    content: str, field_name: str, default_version: str = "1.0.0"
) -> str:
    """Fix version field with simple string default"""
    # Match: field_name: str = Field(default="1.0.0", ...)
    pattern = rf'({field_name}:\s+)str(\s*=\s*Field\(\s*default=)"{default_version}"'

    # Parse version
    parts = default_version.split(".")
    major, minor, patch = parts[0], parts[1], parts[2] if len(parts) > 2 else "0"

    replacement = rf"\1ModelSemVer\2_factory=lambda: ModelSemVer(major={major}, minor={minor}, patch={patch})"
    return re.sub(pattern, replacement, content)


def ensure_uuid_import(content: str) -> str:
    """Ensure UUID and uuid4 are imported"""
    lines = content.split("\n")

    has_uuid_import = any("from uuid import" in line for line in lines)
    has_uuid = any("UUID" in line and "import" in line for line in lines)
    has_uuid4 = any("uuid4" in line and "import" in line for line in lines)

    if has_uuid_import:
        # Update existing import
        for i, line in enumerate(lines):
            if "from uuid import" in line and "UUID" not in line:
                # Add UUID to import
                lines[i] = line.replace("from uuid import", "from uuid import UUID, ")
            elif "from uuid import" in line and "uuid4" not in line and "UUID" in line:
                # Add uuid4 to import
                lines[i] = line.replace(
                    "from uuid import UUID", "from uuid import UUID, uuid4"
                )
    else:
        # Add new import after other imports
        for i, line in enumerate(lines):
            if line.startswith("from pydantic import") or line.startswith(
                "from omnibase_core"
            ):
                lines.insert(i, "from uuid import UUID, uuid4\n")
                break

    return "\n".join(lines)


def ensure_semver_import(content: str) -> str:
    """Ensure ModelSemVer is imported"""
    if "from omnibase_core.models.core.model_semver import ModelSemVer" in content:
        return content

    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("from omnibase_core.models") or line.startswith(
            "from pydantic"
        ):
            lines.insert(
                i + 1,
                "from omnibase_core.models.core.model_semver import ModelSemVer\n",
            )
            break

    return "\n".join(lines)


def fix_file(file_path: Path, field_fixes: dict[str, str]) -> bool:
    """
    Fix a file with specified field transformations.

    field_fixes: dict mapping field_name -> type ("UUID" or "ModelSemVer")
    """
    try:
        content = file_path.read_text()
        original = content

        needs_uuid = False
        needs_semver = False

        for field_name, target_type in field_fixes.items():
            if target_type == "UUID":
                content = fix_id_field_simple(content, field_name)
                needs_uuid = True
            elif target_type == "ModelSemVer":
                # For now, just change the type - manual fix for default values
                pattern = rf"(\s+{field_name}:\s+)str(\s*=\s*Field\()"
                content = re.sub(pattern, r"\1ModelSemVer\2", content)
                needs_semver = True

        # Fix uuid4 factories
        if needs_uuid:
            content = fix_id_field_with_uuid_factory(content)
            content = ensure_uuid_import(content)

        if needs_semver:
            content = ensure_semver_import(content)

        if content != original:
            file_path.write_text(content)
            print(f"✅ Fixed: {file_path.relative_to(Path.cwd())}")
            return True
        else:
            print(f"⏭️  No changes: {file_path.relative_to(Path.cwd())}")
            return False

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False


def main():
    """Fix all files with string ID/version violations"""

    base = Path("/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core")

    files_to_fix = {
        base
        / "models/discovery/model_event_descriptor.py": {
            "event_schema_version": "ModelSemVer"
        },
        base
        / "models/discovery/model_tool_response_event.py": {
            "target_node_id": "UUID",
            "requester_id": "UUID",
        },
        base
        / "models/discovery/model_nodehealthevent.py": {
            "service_id": "UUID",
            "check_id": "UUID",
        },
        base
        / "models/core/model_event_envelope.py": {
            "envelope_id": "UUID",
            "source_node_id": "UUID",
            "node_id": "UUID",
        },
        base
        / "models/security/model_permission_scope.py": {
            "scope_id": "UUID",
        },
        base
        / "models/security/model_detection_pattern.py": {
            "pattern_id": "UUID",
        },
        base
        / "models/core/model_system_data.py": {
            "system_id": "UUID",
        },
        base
        / "models/core/model_instance_metadata.py": {
            "deployment_id": "UUID",
        },
        base
        / "models/service/model_event_bus_input_state.py": {
            "correlation_id": "UUID",
            "event_id": "UUID",
            "version": "ModelSemVer",
        },
    }

    fixed = 0
    for file_path, field_fixes in files_to_fix.items():
        if file_path.exists():
            if fix_file(file_path, field_fixes):
                fixed += 1
        else:
            print(f"⚠️  File not found: {file_path}")

    print(f"\n📊 Summary: Fixed {fixed}/{len(files_to_fix)} files")
    return 0 if fixed == len(files_to_fix) else 1


if __name__ == "__main__":
    sys.exit(main())
