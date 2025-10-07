#!/usr/bin/env python3
"""Batch fix MyPy errors with specific patterns."""

import re
from pathlib import Path
from typing import Dict, List, Tuple

# Patterns to fix: (regex_pattern, replacement, description)
FIXES: List[Tuple[str, str, str]] = [
    # Enum import fixes - remove "Model" prefix from enum names
    (r"\bModelEnumTransitionType\b", "EnumTransitionType", "Fix EnumTransitionType"),
    (
        r"\bModelToolCapabilityLevel\b",
        "EnumToolCapabilityLevel",
        "Fix EnumToolCapabilityLevel",
    ),
    (r"\bModelToolCategory\b", "EnumToolCategory", "Fix EnumToolCategory"),
    (
        r"\bModelToolCompatibilityMode\b",
        "EnumToolCompatibilityMode",
        "Fix EnumToolCompatibilityMode",
    ),
    (
        r"\bModelToolRegistrationStatus\b",
        "EnumToolRegistrationStatus",
        "Fix EnumToolRegistrationStatus",
    ),
    (
        r"\bModelMetadataToolComplexity\b",
        "EnumMetadataToolComplexity",
        "Fix EnumMetadataToolComplexity",
    ),
    (
        r"\bModelMetadataToolStatus\b",
        "EnumMetadataToolStatus",
        "Fix EnumMetadataToolStatus",
    ),
    (r"\bModelMetadataToolType\b", "EnumMetadataToolType", "Fix EnumMetadataToolType"),
    (
        r"\bModelFallbackStrategyType\b",
        "EnumFallbackStrategyType",
        "Fix EnumFallbackStrategyType",
    ),
    # Module import fixes
    (
        r"from pydantic_core import ValidationInfo",
        "from pydantic import ValidationInfo",
        "Fix ValidationInfo import",
    ),
    # Missing type parameters
    (r":\s*set\s*([|\[])", r": set[str]\1", "Fix set type parameter"),
    (r"Pattern\s*([|\]])", r"Pattern[str]\1", "Fix Pattern type parameter"),
    # Self-circular imports - remove
    (
        r"from omnibase_core\.models\.metadata\.model_versionunion import ModelTypedDictVersionDict",
        "",
        "Remove circular import",
    ),
    (
        r"from omnibase_core\.models\.core\.model_base_result import ModelBaseResult",
        "",
        "Remove circular import",
    ),
    (
        r"from omnibase_core\.models\.security\.model_secret_manager import ModelSecretManager",
        "",
        "Remove circular import",
    ),
]

# File-specific fixes that need context
FILE_SPECIFIC_FIXES: Dict[str, List[Tuple[str, str]]] = {
    "model_enhanced_tool_collection.py": [
        (
            "from omnibase_core.models.core.model_tool_metadata import (",
            "from omnibase_core.models.core.model_tool_metadata import (\n    EnumToolCapabilityLevel,\n    EnumToolCompatibilityMode,\n    EnumToolRegistrationStatus,",
        ),
    ],
    "model_tool_collection.py": [
        (
            "from omnibase_core.models.core.model_metadata_tool_collection import (",
            "from omnibase_core.models.core.model_metadata_tool_collection import (\n    EnumMetadataToolComplexity,\n    EnumMetadataToolStatus,\n    EnumMetadataToolType,",
        ),
    ],
}


def fix_file(file_path: Path) -> int:
    """Fix a single file. Returns number of changes made."""
    content = file_path.read_text()
    original = content
    changes = 0

    # Apply global regex fixes
    for pattern, replacement, description in FIXES:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            change_count = len(re.findall(pattern, content))
            content = new_content
            changes += change_count
            if change_count > 0:
                print(f"  - {description}: {change_count} changes")

    # Apply file-specific fixes
    filename = file_path.name
    if filename in FILE_SPECIFIC_FIXES:
        for old_text, new_text in FILE_SPECIFIC_FIXES[filename]:
            if old_text in content:
                content = content.replace(old_text, new_text)
                changes += 1
                print(f"  - File-specific fix applied")

    if content != original:
        file_path.write_text(content)
        return changes

    return 0


def main():
    """Main function to fix all files."""
    src_dir = Path("/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core")
    total_changes = 0
    files_changed = 0

    for py_file in src_dir.rglob("*.py"):
        changes = fix_file(py_file)
        if changes > 0:
            print(f"\nFixed {changes} issues in {py_file.name}")
            total_changes += changes
            files_changed += 1

    print(f"\n=== Summary ===")
    print(f"Files changed: {files_changed}")
    print(f"Total changes: {total_changes}")


if __name__ == "__main__":
    main()
