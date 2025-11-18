#!/usr/bin/env python3
"""
Apply automatic fixes for broken documentation links.

This script applies the 5 quick fixes identified in the link validation:
1. README.md:377 - Fix Threading Guide path
2. README.md:378 - Fix Patterns Catalog filename
3. TERMINOLOGY_AUDIT_REPORT.md:297 - Fix migration guide path
4. MODEL_INTENT_ARCHITECTURE.md:965 - Fix reducer node anchor
5. MODEL_INTENT_ARCHITECTURE.md:966 - Fix effect node anchor
"""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Fix definitions: (file_path, old_text, new_text, description)
FIXES = [
    (
        "README.md",
        "[Threading Guide](docs/reference/THREADING.md)",
        "[Threading Guide](docs/guides/THREADING.md)",
        "Fix Threading Guide path"
    ),
    (
        "README.md",
        "[Patterns Catalog](docs/guides/node-building/07-patterns-catalog.md)",
        "[Patterns Catalog](docs/guides/node-building/07_PATTERNS_CATALOG.md)",
        "Fix Patterns Catalog filename"
    ),
    (
        "docs/quality/TERMINOLOGY_AUDIT_REPORT.md",
        "[MIGRATING_TO_DECLARATIVE_NODES.md](../MIGRATING_TO_DECLARATIVE_NODES.md)",
        "[MIGRATING_TO_DECLARATIVE_NODES.md](../guides/MIGRATING_TO_DECLARATIVE_NODES.md)",
        "Fix migration guide path"
    ),
    (
        "docs/architecture/MODEL_INTENT_ARCHITECTURE.md",
        "[Reducer Node Guide](../guides/node-building/02_NODE_TYPES.md#reducer-nodes)",
        "[Reducer Node Guide](../guides/node-building/02_NODE_TYPES.md#reducer-node)",
        "Fix reducer node anchor (singular)"
    ),
    (
        "docs/architecture/MODEL_INTENT_ARCHITECTURE.md",
        "[Effect Node Guide](../guides/node-building/02_NODE_TYPES.md#effect-nodes)",
        "[Effect Node Guide](../guides/node-building/02_NODE_TYPES.md#effect-node)",
        "Fix effect node anchor (singular)"
    ),
]


def apply_fixes():
    """Apply all fixes."""
    print("🔧 Applying documentation link fixes...\n")

    success_count = 0
    failure_count = 0

    for file_path, old_text, new_text, description in FIXES:
        full_path = BASE_DIR / file_path

        print(f"📝 {description}")
        print(f"   File: {file_path}")

        if not full_path.exists():
            print(f"   ❌ File not found: {full_path}")
            failure_count += 1
            continue

        # Read file
        try:
            content = full_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            failure_count += 1
            continue

        # Check if old text exists
        if old_text not in content:
            print(f"   ⚠️  Text not found (may already be fixed)")
            continue

        # Apply fix
        new_content = content.replace(old_text, new_text)

        # Verify fix was applied
        if new_content == content:
            print(f"   ❌ Fix not applied")
            failure_count += 1
            continue

        # Write back
        try:
            full_path.write_text(new_content, encoding='utf-8')
            print(f"   ✅ Fixed")
            success_count += 1
        except Exception as e:
            print(f"   ❌ Error writing file: {e}")
            failure_count += 1

        print()

    print("=" * 80)
    print(f"Summary: {success_count} fixes applied, {failure_count} failures")
    print("=" * 80)

    if success_count > 0:
        print("\n✅ Run validation script to confirm:")
        print("   poetry run python scripts/validate_docs_links.py")


if __name__ == "__main__":
    apply_fixes()
