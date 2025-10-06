#!/usr/bin/env python3
"""
Fix ONEX String Version Anti-Pattern violations.

Automatically converts:
- str ID fields to UUID
- str version fields to ModelSemVer
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class StringVersionFixer:
    """Fix string version/ID anti-patterns in Python files."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text()
        self.lines = self.content.splitlines(keepends=True)
        self.needs_uuid_import = False
        self.needs_semver_import = False
        self.changes_made = False

    def fix_file(self) -> bool:
        """Fix all violations in the file."""
        # Fix ID fields (ending with _id or named exactly 'id')
        self._fix_id_fields()

        # Fix version fields
        self._fix_version_fields()

        if not self.changes_made:
            return False

        # Add necessary imports
        self._add_imports()

        # Write back to file
        self.file_path.write_text("".join(self.lines))
        return True

    def _fix_id_fields(self):
        """Convert str ID fields to UUID."""
        # Pattern: field_name_id: str = Field(...)
        # Pattern: field_name_id: str | None = Field(...)
        id_pattern = re.compile(
            r'^(\s+)(\w*_?id):\s+str(\s+\|?\s*None)?\s*=\s*Field\('
        )

        for i, line in enumerate(self.lines):
            match = id_pattern.match(line)
            if match:
                indent = match.group(1)
                field_name = match.group(2)
                optional_part = match.group(3) or ""

                # Replace str with UUID
                new_line = line.replace(
                    f": str{optional_part} =",
                    f": UUID{optional_part} ="
                )
                self.lines[i] = new_line
                self.needs_uuid_import = True
                self.changes_made = True
                print(f"  Fixed ID field: {field_name} in {self.file_path.name}:{i+1}")

    def _fix_version_fields(self):
        """Convert str version fields to ModelSemVer."""
        # Pattern: field_name_version: str = Field(...)
        # Pattern: version: str = Field(...)
        version_pattern = re.compile(
            r'^(\s+)(\w*_?version):\s+str(\s+\|?\s*None)?\s*=\s*Field\('
        )

        for i, line in enumerate(self.lines):
            match = version_pattern.match(line)
            if match:
                indent = match.group(1)
                field_name = match.group(2)
                optional_part = match.group(3) or ""

                # Replace str with ModelSemVer
                new_line = line.replace(
                    f": str{optional_part} =",
                    f": ModelSemVer{optional_part} ="
                )
                self.lines[i] = new_line
                self.needs_semver_import = True
                self.changes_made = True
                print(f"  Fixed version field: {field_name} in {self.file_path.name}:{i+1}")

    def _add_imports(self):
        """Add necessary imports to the file."""
        import_section_end = self._find_import_section_end()

        new_imports = []
        if self.needs_uuid_import and "from uuid import UUID" not in self.content:
            new_imports.append("from uuid import UUID\n")

        if self.needs_semver_import and "ModelSemVer" not in self.content:
            new_imports.append("from omnibase_core.models.metadata.model_semver import ModelSemVer\n")

        if new_imports:
            # Insert after existing imports
            for imp in reversed(new_imports):
                self.lines.insert(import_section_end, imp)
            print(f"  Added imports to {self.file_path.name}")

    def _find_import_section_end(self) -> int:
        """Find the end of the import section."""
        last_import_line = 0

        for i, line in enumerate(self.lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                last_import_line = i + 1
            elif stripped and not stripped.startswith("#") and last_import_line > 0:
                # Found first non-import, non-comment line
                break

        return last_import_line


def fix_violations_in_file(file_path: Path) -> bool:
    """Fix violations in a single file."""
    try:
        fixer = StringVersionFixer(file_path)
        return fixer.fix_file()
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    # List of files from the validation output
    files_to_fix = [
        "src/omnibase_core/models/security/model_encryption_metadata.py",
        "src/omnibase_core/models/service/model_error_details.py",
        "src/omnibase_core/models/core/model_route_hop.py",
        "src/omnibase_core/models/core/model_node_information.py",
        "src/omnibase_core/models/health/model_tool_health.py",
        "src/omnibase_core/models/common/model_validation_metadata.py",
        "src/omnibase_core/models/core/model_yaml_metadata.py",
        "src/omnibase_core/models/core/model_template_context.py",
        "src/omnibase_core/models/core/model_group_dependency.py",
        "src/omnibase_core/models/service/model_workflow_status_result.py",
        "src/omnibase_core/models/core/model_registry_reference.py",
        "src/omnibase_core/models/configuration/model_handler_protocol.py",
        "src/omnibase_core/models/core/model_checkpoint_data.py",
        "src/omnibase_core/models/configuration/model_load_balancing_policy.py",
        "src/omnibase_core/models/configuration/model_onex_metadata.py",
        "src/omnibase_core/models/core/model_parse_metadata.py",
        "src/omnibase_core/models/core/model_registry_configuration.py",
        "src/omnibase_core/models/security/model_secure_event_envelope_class.py",
        "src/omnibase_core/models/workflows/model_workflow_input_state.py",
        "src/omnibase_core/models/service/model_custom_fields.py",
        "src/omnibase_core/models/core/model_tool_implementation.py",
        "src/omnibase_core/models/core/model_error_summary.py",
        "src/omnibase_core/models/core/model_node_execution_result.py",
        "src/omnibase_core/models/security/model_signature_chain.py",
        "src/omnibase_core/models/discovery/model_tool_discovery_response.py",
        "src/omnibase_core/models/discovery/model_hub_registration_event.py",
    ]

    print("🔧 Fixing ONEX String Version Anti-Pattern violations...\n")

    project_root = Path(__file__).parent.parent
    fixed_count = 0
    error_count = 0

    for file_rel in files_to_fix:
        file_path = project_root / file_rel
        if not file_path.exists():
            print(f"⚠️  File not found: {file_rel}")
            continue

        print(f"\n📁 Processing: {file_rel}")
        if fix_violations_in_file(file_path):
            fixed_count += 1
            print(f"✅ Fixed {file_rel}")
        else:
            print(f"ℹ️  No changes needed for {file_rel}")

    print(f"\n{'='*60}")
    print(f"✅ Fixed {fixed_count} files")
    print(f"{'='*60}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
