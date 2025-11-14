#!/usr/bin/env python3
"""
Import Pattern Fixer

Automatically converts multi-level relative imports to absolute imports
following ONEX standards.
"""

import re
import sys
from pathlib import Path


def fix_import_patterns(file_path: Path) -> int:
    """Fix import patterns in a single file and return number of changes."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content
        changes = 0

        # Pattern replacements for multi-level relative imports
        replacements = [
            # Triple-dot imports to enums
            (r"from \.\.\.enums\.", "from omnibase_core.enums."),
            # Triple-dot imports to exceptions
            (r"from \.\.\.exceptions\.", "from omnibase_core.exceptions."),
            # Triple-dot imports to protocols_local
            (r"from \.\.\.protocols_local\.", "from omnibase_core.protocols_local."),
            # Triple-dot imports to utils
            (r"from \.\.\.utils\.", "from omnibase_core.utils."),
            # Triple-dot imports to models (direct)
            (r"from \.\.\.models\.", "from omnibase_core.models."),
            # Double-dot imports to models subdirectories
            (r"from \.\.common\.", "from omnibase_core.models.common."),
            (r"from \.\.metadata\.", "from omnibase_core.models.metadata."),
            (r"from \.\.infrastructure\.", "from omnibase_core.models.infrastructure."),
            (r"from \.\.core\.", "from omnibase_core.models.core."),
            (r"from \.\.connections\.", "from omnibase_core.models.connections."),
            (r"from \.\.nodes\.", "from omnibase_core.models.nodes."),
            (r"from \.\.cli\.", "from omnibase_core.models.cli."),
            (r"from \.\.config\.", "from omnibase_core.models.examples."),
            (r"from \.\.contracts\.", "from omnibase_core.models.contracts."),
            (r"from \.\.validation\.", "from omnibase_core.models.validation."),
            (r"from \.\.utils\.", "from omnibase_core.models.utils."),
        ]

        # Apply replacements
        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                matches = len(re.findall(pattern, content))
                changes += matches
                content = new_content
                print(
                    f"  📝 {file_path.name}: Fixed {matches} imports matching {pattern}"
                )

        # Write back if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return changes

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return 0


def fix_directory(directory: Path) -> int:
    """Fix all Python files in a directory recursively."""
    total_changes = 0

    print(f"🔧 Processing directory: {directory}")

    # Find all Python files
    python_files = list(directory.glob("**/*.py"))

    # Skip certain files
    python_files = [f for f in python_files if "__pycache__" not in str(f)]

    for file_path in python_files:
        changes = fix_import_patterns(file_path)
        total_changes += changes

    return total_changes


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        target_path = Path("src")

    print(f"🚀 Starting import pattern fixes for: {target_path}")
    print("=" * 60)

    if not target_path.exists():
        print(f"❌ Path does not exist: {target_path}")
        sys.exit(1)

    total_changes = fix_directory(target_path)

    print("=" * 60)
    print("✅ Import pattern fixes complete!")
    print(f"📊 Total changes made: {total_changes}")

    if total_changes > 0:
        print("\n🔍 Running validation to verify fixes...")
        # Run the validation script to check results
        import subprocess

        try:
            result = subprocess.run(
                [
                    "poetry",
                    "run",
                    "python",
                    "scripts/validation/validate-import-patterns.py",
                    str(target_path),
                    "--max-violations",
                    "0",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                print("✅ All import patterns fixed successfully!")
            else:
                print("⚠️  Some violations may remain:")
                print(result.stdout)
        except Exception as e:
            print(f"⚠️  Could not run validation: {e}")


if __name__ == "__main__":
    main()
