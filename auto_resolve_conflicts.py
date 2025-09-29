#!/usr/bin/env python3
"""
Automated merge conflict resolver for ONEX model files.

Follows the established pattern:
- Keep our protocol method implementations
- Take main's improved imports and model_config
"""

import re
import subprocess
import sys


def get_unmerged_files():
    """Get list of files with unresolved conflicts."""
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    files = []
    for line in result.stdout.strip().split("\n"):
        if line.startswith("UU "):
            files.append(line[3:])
    return files


def resolve_import_conflict(content):
    """Resolve import conflicts by taking main's version."""
    # Pattern for import conflicts
    import_pattern = r"<<<<<<< HEAD\nfrom typing import Any\n\nfrom pydantic import BaseModel, Field\n=======\nfrom typing import Any, Union\n\nfrom pydantic import BaseModel, Field, field_validator\n>>>>>>> origin/main"

    replacement = "from typing import Any, Union\n\nfrom pydantic import BaseModel, Field, field_validator"

    return re.sub(import_pattern, replacement, content, flags=re.MULTILINE)


def resolve_protocol_config_conflict(content):
    """Resolve protocol vs model_config conflicts by combining both."""

    # Find the conflict section
    conflict_pattern = r"<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> origin/main"

    def replace_conflict(match):
        our_section = match.group(1)
        main_section = match.group(2)

        # If our section has protocol methods and main has model_config
        if (
            "# Protocol method implementations" in our_section
            and "model_config = {" in main_section
        ):
            # Combine them - model_config first, then protocols
            return main_section + "\n\n" + our_section
        else:
            # For other conflicts, prefer main's changes
            return main_section

    return re.sub(
        conflict_pattern, replace_conflict, content, flags=re.MULTILINE | re.DOTALL
    )


def resolve_file_conflicts(filepath):
    """Resolve conflicts in a single file."""
    try:
        with open(filepath, "r") as f:
            content = f.read()

        # Check if file has conflicts
        if "<<<<<<< HEAD" not in content:
            return False

        print(f"Resolving conflicts in {filepath}")

        # Apply conflict resolutions
        content = resolve_import_conflict(content)
        content = resolve_protocol_config_conflict(content)

        # Check if all conflicts are resolved
        if "<<<<<<< HEAD" in content:
            print(f"  Warning: Some conflicts remain in {filepath}")
            return False

        # Write resolved content
        with open(filepath, "w") as f:
            f.write(content)

        # Stage the resolved file
        subprocess.run(["git", "add", filepath])
        print(f"  ✓ Resolved and staged {filepath}")
        return True

    except Exception as e:
        print(f"  Error resolving {filepath}: {e}")
        return False


def main():
    """Main resolution process."""
    unmerged_files = get_unmerged_files()

    if not unmerged_files:
        print("No unmerged files found.")
        return

    print(f"Found {len(unmerged_files)} files with conflicts.")

    # Focus on model files first
    model_files = [f for f in unmerged_files if "/models/" in f and f.endswith(".py")]

    resolved_count = 0
    for filepath in model_files:
        if resolve_file_conflicts(filepath):
            resolved_count += 1

    print(f"\nResolved {resolved_count} out of {len(model_files)} model files.")

    # Check remaining conflicts
    remaining = get_unmerged_files()
    print(f"Remaining unmerged files: {len(remaining)}")


if __name__ == "__main__":
    main()
