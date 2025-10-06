#!/usr/bin/env python3
"""
Script to fix UUID type errors in discovery models.
Converts node_id: str to node_id: UUID in factory methods.
"""

import re
from pathlib import Path

# Files to fix based on MyPy output
FILES_TO_FIX = [
    "src/omnibase_core/models/discovery/model_tool_response_event.py",
    "src/omnibase_core/models/discovery/model_tool_invocation_event.py",
    "src/omnibase_core/models/discovery/model_request_introspection_event.py",
    "src/omnibase_core/models/discovery/model_nodeintrospectionevent.py",
    "src/omnibase_core/models/discovery/model_tooldiscoveryresponse.py",
    "src/omnibase_core/models/core/model_onex_event.py",
]


def fix_uuid_imports(content: str) -> str:
    """Add UUID import if not present."""
    # Check if UUID is already imported
    if "from uuid import UUID" in content or "from uuid import uuid4, UUID" in content:
        return content

    # Find the first import statement and add UUID import before it
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("from uuid import"):
            # Already has uuid import, just add UUID if needed
            if "UUID" not in line:
                lines[i] = line.replace("from uuid import", "from uuid import UUID,")
            return "\n".join(lines)
        elif line.startswith("from ") or line.startswith("import "):
            # Insert UUID import before first import
            lines.insert(i, "from uuid import UUID")
            return "\n".join(lines)

    return content


def fix_node_id_parameters(content: str) -> str:
    """Fix node_id: str to node_id: UUID in method parameters."""
    # Pattern for node_id: str in function parameters
    pattern = r"\bnode_id:\s*str\b"
    replacement = "node_id: UUID"
    return re.sub(pattern, replacement, content)


def fix_requester_id_parameters(content: str) -> str:
    """Fix requester_id: str | UUID to requester_id: UUID."""
    pattern = r"\brequester_id:\s*str\s*\|\s*UUID\b"
    replacement = "requester_id: UUID"
    return re.sub(pattern, replacement, content)


def process_file(file_path: Path) -> bool:
    """Process a single file and return True if changes were made."""
    if not file_path.exists():
        print(f"Warning: File not found: {file_path}")
        return False

    content = file_path.read_text()
    original_content = content

    # Apply fixes
    content = fix_uuid_imports(content)
    content = fix_node_id_parameters(content)
    content = fix_requester_id_parameters(content)

    if content != original_content:
        file_path.write_text(content)
        print(f"✓ Fixed: {file_path}")
        return True
    else:
        print(f"  No changes: {file_path}")
        return False


def main():
    base_path = Path(__file__).parent.parent
    fixed_count = 0

    print("Fixing UUID type errors in discovery models...")
    print("=" * 60)

    for file_rel_path in FILES_TO_FIX:
        file_path = base_path / file_rel_path
        if process_file(file_path):
            fixed_count += 1

    print("=" * 60)
    print(f"Fixed {fixed_count} / {len(FILES_TO_FIX)} files")


if __name__ == "__main__":
    main()
