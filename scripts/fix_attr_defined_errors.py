#!/usr/bin/env python3
"""Script to fix attr-defined MyPy errors with clear mappings."""

import re
from pathlib import Path

# Map of incorrect attribute/class names to correct ones
FIXES = {
    # TypedDict fixes
    "ModelTypedDictGenericMetadataDict": "TypedDictMetadataDict",

    # Enum fixes (Model prefix should not be there)
    "ModelEnumTransitionType": "EnumTransitionType",
    "ModelToolCapabilityLevel": "EnumToolCapabilityLevel",
    "ModelToolCategory": "EnumToolCategory",
    "ModelToolCompatibilityMode": "EnumToolCompatibilityMode",
    "ModelToolRegistrationStatus": "EnumToolRegistrationStatus",
    "ModelMetadataToolComplexity": "EnumMetadataToolComplexity",
    "ModelMetadataToolStatus": "EnumMetadataToolStatus",
    "ModelMetadataToolType": "EnumMetadataToolType",

    # Class name fixes
    "ModelExamples": "ModelExample",
    "ModelNodeCapabilities": "ModelNodeCapability",
    "CanonicalYAMLSerializer": "MixinCanonicalYAMLSerializer",

    # Attribute name fixes (need context-specific handling)
    # These will be handled separately
}

# Attribute mappings (object.old_attr → object.new_attr)
ATTR_FIXES = {
    "ModelHubConfiguration": {
        ".domain": ".domain_id",
        ".managed_tools": ".managed_tool_ids",
    },
}

def fix_file(file_path: Path) -> int:
    """Fix a single file. Returns number of changes made."""
    content = file_path.read_text()
    original = content
    changes = 0

    # Fix class/module name imports and references
    for old_name, new_name in FIXES.items():
        # Fix imports
        pattern = rf'\bfrom\s+([a-z_\.]+)\s+import\s+.*\b{old_name}\b'
        if re.search(pattern, content):
            content = re.sub(
                rf'\b{old_name}\b',
                new_name,
                content
            )
            changes += content.count(new_name) - original.count(new_name)

    # Fix attribute access
    for class_name, attr_map in ATTR_FIXES.items():
        for old_attr, new_attr in attr_map.items():
            # Look for pattern like: variable.old_attr
            pattern = rf'(\w+){re.escape(old_attr)}\b'
            if re.search(pattern, content):
                content = re.sub(pattern, rf'\1{new_attr}', content)
                changes += 1

    if content != original:
        file_path.write_text(content)
        print(f"Fixed {changes} issues in {file_path}")
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
            total_changes += changes
            files_changed += 1

    print(f"\n=== Summary ===")
    print(f"Files changed: {files_changed}")
    print(f"Total changes: {total_changes}")

if __name__ == "__main__":
    main()
