#!/usr/bin/env python3
"""
Efficient batch fix for MyPy name-defined errors.
Parses errors once and applies all fixes in a single pass.
"""

import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

ROOT_DIR = Path("/Volumes/PRO-G40/Code/omnibase_core")
SRC_DIR = ROOT_DIR / "src" / "omnibase_core"

# Standard library imports
STDLIB_IMPORTS = {
    "hashlib": "import hashlib",
    "re": "import re",
    "Path": "from pathlib import Path",
    "cast": "from typing import cast",
    "UUID": "from uuid import UUID",
}

# Internal model imports
INTERNAL_IMPORTS = {
    "ModelOnexError": "from omnibase_core.errors.model_onex_error import ModelOnexError",
    "EnumCoreErrorCode": "from omnibase_core.errors.error_codes import EnumCoreErrorCode",
    "ModelErrorContext": "from omnibase_core.models.common.model_error_context import ModelErrorContext",
    "ModelSchemaValue": "from omnibase_core.models.common.model_schema_value import ModelSchemaValue",
    "EnumAuditAction": "from omnibase_core.enums.enum_audit_action import EnumAuditAction",
    "EnumSecurityLevel": "from omnibase_core.enums.enum_security_level import EnumSecurityLevel",
    "ModelRetryPolicy": "from omnibase_core.models.configuration.model_retry_policy import ModelRetryPolicy",
    "ModelSemVer": "from omnibase_core.models.metadata.model_semver import ModelSemVer",
    "EnumStatusMigrationValidator": "from omnibase_core.enums.enum_status_migration import EnumStatusMigrationValidator",
}

# Wrong attribute name corrections
ATTR_CORRECTIONS = {
    "ModelTypedDictGenericMetadataDict": "TypedDictMetadataDict",
    "ModelEnumTransitionType": "EnumTransitionType",
}


def run_mypy_once() -> str:
    """Run MyPy once and cache the output."""
    print("Running MyPy to collect all errors...")
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/", "--no-error-summary"],
        capture_output=True,
        text=True,
        cwd=ROOT_DIR,
        check=False,
    )
    return result.stdout + result.stderr


def parse_errors(mypy_output: str) -> dict[str, list[dict]]:
    """Parse MyPy output and group errors by file."""
    errors_by_file = defaultdict(list)

    for line in mypy_output.split("\n"):
        # Parse: file.py:line: error: Message  [error-type]
        match = re.match(r"^(.*?):(\d+): error: (.*?)\s+\[([\w-]+)\]$", line.strip())
        if match:
            filepath, lineno, message, error_type = match.groups()

            if error_type not in ("name-defined", "attr-defined"):
                continue

            errors_by_file[filepath].append(
                {
                    "line": int(lineno),
                    "message": message,
                    "type": error_type,
                }
            )

    return dict(errors_by_file)


def extract_missing_names(errors: list[dict]) -> set[str]:
    """Extract missing names from error messages."""
    names = set()
    for error in errors:
        match = re.search(r'Name "(\w+)" is not defined', error["message"])
        if match:
            names.add(match.group(1))
    return names


def has_import(content: str, import_stmt: str) -> bool:
    """Check if import already exists."""
    # Simple check for the import line
    if import_stmt in content:
        return True

    # Check for the imported name
    if " import " in import_stmt:
        parts = import_stmt.split(" import ")
        if len(parts) == 2:
            name = parts[1].strip()
            # Check if name is imported from any module
            if re.search(rf"\bimport\s+.*\b{re.escape(name)}\b", content):
                return True

    return False


def find_import_insert_position(lines: list[str]) -> int:
    """Find where to insert new imports."""
    last_import = 0
    in_docstring = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if stripped.startswith(('"""', "'''")):
            if not in_docstring:
                in_docstring = True
                if not (stripped.endswith(('"""', "'''"))):
                    continue
                in_docstring = False
            elif in_docstring:
                in_docstring = False
            continue

        if in_docstring:
            continue

        # Track imports
        if stripped.startswith(("from ", "import ")):
            last_import = i

    return last_import + 1 if last_import > 0 else 0


def fix_file(filepath: str, errors: list[dict]) -> int:
    """Fix all errors in a single file."""
    path = Path(filepath)
    if not path.exists():
        return 0

    content = path.read_text()
    lines = content.split("\n")

    # Collect all needed imports
    missing_names = extract_missing_names(errors)
    imports_to_add = []

    for name in missing_names:
        if name in STDLIB_IMPORTS:
            import_stmt = STDLIB_IMPORTS[name]
            if not has_import(content, import_stmt):
                imports_to_add.append(import_stmt)
        elif name in INTERNAL_IMPORTS:
            import_stmt = INTERNAL_IMPORTS[name]
            if not has_import(content, import_stmt):
                imports_to_add.append(import_stmt)

    # Fix wrong attribute names
    modified = False
    for old_name, new_name in ATTR_CORRECTIONS.items():
        if old_name in content:
            content = content.replace(old_name, new_name)
            lines = content.split("\n")
            modified = True
            print(f"    Renamed: {old_name} → {new_name}")

    # Add missing imports
    if imports_to_add:
        insert_pos = find_import_insert_position(lines)

        # Insert all imports
        for import_stmt in sorted(imports_to_add):
            lines.insert(insert_pos, import_stmt)
            insert_pos += 1
            print(f"    Added: {import_stmt}")
            modified = True

    if modified:
        path.write_text("\n".join(lines))
        return len(imports_to_add) + (
            1 if any(old_name in content for old_name in ATTR_CORRECTIONS) else 0
        )

    return 0


def main():
    """Main execution."""
    print("=" * 80)
    print("Batch Fix for MyPy Name-Defined Errors")
    print("=" * 80)

    # Run MyPy once
    mypy_output = run_mypy_once()

    # Parse all errors
    errors_by_file = parse_errors(mypy_output)
    total_errors = sum(len(errs) for errs in errors_by_file.values())

    print(
        f"Found {total_errors} name-defined/attr-defined errors in {len(errors_by_file)} files"
    )
    print()

    # Fix files in priority order
    priority_paths = [
        "models/core/",
        "models/common/",
        "models/",
        "mixins/",
        "infrastructure/",
    ]

    total_fixes = 0

    for priority in priority_paths:
        matching_files = [fp for fp in errors_by_file if priority in fp]

        for filepath in sorted(matching_files):
            print(f"\n{Path(filepath).name}:")
            fixes = fix_file(filepath, errors_by_file[filepath])
            total_fixes += fixes

    # Fix remaining files
    all_priority_files = {
        fp for fp in errors_by_file if any(p in fp for p in priority_paths)
    }
    remaining = set(errors_by_file.keys()) - all_priority_files

    for filepath in sorted(remaining):
        print(f"\n{Path(filepath).name}:")
        fixes = fix_file(filepath, errors_by_file[filepath])
        total_fixes += fixes

    print("\n" + "=" * 80)
    print(f"Applied {total_fixes} fixes across {len(errors_by_file)} files")
    print("=" * 80)


if __name__ == "__main__":
    main()
