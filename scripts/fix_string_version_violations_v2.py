#!/usr/bin/env python3
"""
Fix ONEX String Version Anti-Pattern violations - Comprehensive version.

Automatically converts:
- str ID fields to UUID (in fields, parameters, type hints)
- str version fields to ModelSemVer (in fields, parameters, type hints)
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple


class ComprehensiveStringVersionFixer:
    """Fix all string version/ID anti-patterns in Python files."""

    # ID field patterns (field names ending with _id or exactly "id")
    ID_PATTERNS = [
        r"\b(\w+_id)\s*:\s*str\b",  # field_id: str
        r"\bid\s*:\s*str\b",  # id: str
    ]

    # Version field patterns
    VERSION_PATTERNS = [
        r"\b(\w+_version)\s*:\s*str\b",  # field_version: str
        r"\bversion\s*:\s*str\b",  # version: str
    ]

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text()
        self.needs_uuid_import = False
        self.needs_semver_import = False
        self.changes_made = False

    def fix_file(self) -> bool:
        """Fix all violations in the file."""
        original_content = self.content

        # Fix ID patterns
        for pattern in self.ID_PATTERNS:
            self.content, id_changed = self._replace_pattern(
                pattern, "UUID", is_id=True
            )
            if id_changed:
                self.changes_made = True
                self.needs_uuid_import = True

        # Fix version patterns
        for pattern in self.VERSION_PATTERNS:
            self.content, ver_changed = self._replace_pattern(
                pattern, "ModelSemVer", is_id=False
            )
            if ver_changed:
                self.changes_made = True
                self.needs_semver_import = True

        if not self.changes_made:
            return False

        # Add necessary imports
        self._add_imports()

        # Write back to file
        self.file_path.write_text(self.content)

        # Report changes
        lines_changed = sum(
            1
            for old, new in zip(
                original_content.split("\n"), self.content.split("\n"), strict=False
            )
            if old != new
        )
        print(f"  ✅ Fixed {lines_changed} lines in {self.file_path.name}")

        return True

    def _replace_pattern(
        self, pattern: str, replacement: str, is_id: bool
    ) -> tuple[str, bool]:
        """Replace a pattern in the content."""
        changed = False
        result = self.content

        # Handle optional types (str | None or Optional[str])
        # Pattern 1: field: str | None
        if is_id:
            pattern_with_optional = pattern.replace(
                r":\s*str\b", r":\s*str\s*\|\s*None"
            )
            result, opt_changed = re.subn(
                pattern_with_optional,
                lambda m: m.group(0).replace("str", replacement),
                result,
            )
            changed = changed or opt_changed > 0

            # Pattern 2: field: Optional[str]
            pattern_optional = pattern.replace(r":\s*str\b", r":\s*Optional\[str\]")
            result, opt2_changed = re.subn(
                pattern_optional,
                lambda m: m.group(0).replace("str", replacement),
                result,
            )
            changed = changed or opt2_changed > 0

        # Basic pattern
        result, basic_changed = re.subn(
            pattern,
            lambda m: m.group(0).replace("str", replacement),
            result,
        )
        changed = changed or basic_changed > 0

        return result, changed

    def _add_imports(self):
        """Add necessary imports to the file."""
        lines = self.content.split("\n")

        # Find import section
        import_end_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                import_end_idx = i + 1
            elif (
                import_end_idx > 0 and line.strip() and not line.strip().startswith("#")
            ):
                break

        # Add imports if needed
        new_imports = []

        if self.needs_uuid_import and "from uuid import UUID" not in self.content:
            new_imports.append("from uuid import UUID")

        if self.needs_semver_import and "ModelSemVer" not in self.content:
            new_imports.append(
                "from omnibase_core.models.metadata.model_semver import ModelSemVer"
            )

        if new_imports:
            for imp in reversed(new_imports):
                lines.insert(import_end_idx, imp)
            self.content = "\n".join(lines)
            print(f"  📦 Added imports: {', '.join(new_imports)}")


def fix_violations_in_file(file_path: Path) -> bool:
    """Fix violations in a single file."""
    try:
        fixer = ComprehensiveStringVersionFixer(file_path)
        return fixer.fix_file()
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False


def get_files_with_violations() -> list[str]:
    """Get list of files with violations from git status or scan."""
    # All Python files in src/omnibase_core
    return [
        "src/omnibase_core/models/core/model_route_hop.py",
        "src/omnibase_core/models/core/model_template_context.py",
        "src/omnibase_core/models/security/model_signature_metadata.py",
        "src/omnibase_core/models/security/model_rule_condition_class.py",
        "src/omnibase_core/models/discovery/model_event_descriptor.py",
        "src/omnibase_core/models/core/model_onex_reply_class.py",
        "src/omnibase_core/mixins/mixin_service_registry.py",
        "src/omnibase_core/models/discovery/model_tooldiscoveryrequest.py",
        "src/omnibase_core/models/core/model_unified_run_metadata.py",
        "src/omnibase_core/models/service/model_node_service_config.py",
        "src/omnibase_core/models/configuration/model_load_balancing_policy.py",
        "src/omnibase_core/models/core/model_group_dependency.py",
        "src/omnibase_core/models/service/model_workflow_status_result.py",
        "src/omnibase_core/models/security/model_secure_event_envelope_class.py",
        "src/omnibase_core/models/health/model_tool_health.py",
    ]


def main():
    """Main entry point."""
    print("🔧 Fixing ONEX String Version Anti-Pattern violations (v2)...\n")

    project_root = Path(__file__).parent.parent
    files_to_fix = get_files_with_violations()

    fixed_count = 0
    skipped_count = 0

    for file_rel in files_to_fix:
        file_path = project_root / file_rel
        if not file_path.exists():
            print(f"⚠️  File not found: {file_rel}")
            continue

        print(f"\n📁 Processing: {file_rel}")
        if fix_violations_in_file(file_path):
            fixed_count += 1
        else:
            print("ℹ️  No changes needed")
            skipped_count += 1

    print(f"\n{'='*60}")
    print(f"✅ Fixed {fixed_count} files, {skipped_count} files unchanged")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
