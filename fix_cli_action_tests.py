#!/usr/bin/env python3
"""
Script to fix CLI Action model tests for ONEX compliance.
Converts direct constructor calls to factory method calls and updates field names.
"""

import re
import sys
from pathlib import Path


def fix_cli_action_tests(file_path: str) -> None:
    """Fix CLI Action test file to use ONEX-compliant patterns."""

    # Read the current file
    with open(file_path, "r") as f:
        content = f.read()

    print(f"Original file size: {len(content)} characters")

    # Pattern 1: Replace direct ModelCliAction() calls with factory method calls
    # This handles multi-line constructor calls
    constructor_pattern = re.compile(
        r"ModelCliAction\(\s*\n?\s*"
        r"(?:action_id=([^,\n]+),?\s*\n?\s*)?"  # Optional action_id
        r"action_name=([^,\n]+),?\s*\n?\s*"  # Required action_name
        r"node_id=([^,\n]+),?\s*\n?\s*"  # Required node_id
        r"node_name=([^,\n]+),?\s*\n?\s*"  # Required node_name (will become node_display_name)
        r"description=([^,\n]+)(?:,?\s*\n?\s*)?"  # Required description
        r"(?:deprecated=([^,\n)]+)(?:,?\s*\n?\s*)?)?"  # Optional deprecated
        r"(?:category=([^,\n)]+)(?:,?\s*\n?\s*)?)?"  # Optional category
        r"\)",
        re.MULTILINE | re.DOTALL,
    )

    def replace_constructor(match):
        action_id = match.group(1)
        action_name = match.group(2)
        node_id = match.group(3)
        node_name = match.group(4)
        description = match.group(5)
        deprecated = match.group(6)
        category = match.group(7)

        # Build the factory method call
        params = [
            f"action_name={action_name}",
            f"node_id={node_id}",
            f"node_name={node_name}",
            f"description={description}",
        ]

        if action_id:
            params.append(f"action_id={action_id}")
        if deprecated:
            params.append(f"deprecated={deprecated}")
        if category:
            params.append(f"category={category}")

        return f"ModelCliAction.from_contract_action(\n            {',\n            '.join(params)},\n        )"

    # Apply the constructor pattern replacement
    new_content = constructor_pattern.sub(replace_constructor, content)

    # Pattern 2: Replace field name references
    field_replacements = [
        (r"\.action_name\b", ".action_display_name"),
        (r"\.node_name\b", ".node_display_name"),
    ]

    for old_pattern, new_pattern in field_replacements:
        new_content = re.sub(old_pattern, new_pattern, new_content)

    # Pattern 3: Handle validation error tests that expect old field names
    # These tests are checking for validation errors on deprecated patterns
    validation_error_pattern = re.compile(
        r"(\s+with pytest\.raises\(ValidationError.*?action_name[^}]*)",
        re.MULTILINE | re.DOTALL,
    )

    def replace_validation_test(match):
        # For validation tests, we need to test the direct constructor still
        # to ensure it properly rejects old-style parameters
        return match.group(1)  # Keep as-is for now, we'll handle these separately

    # Apply validation test replacements
    new_content = validation_error_pattern.sub(replace_validation_test, new_content)

    print(f"New file size: {len(new_content)} characters")
    print(f"Changes made: {len(content) != len(new_content)}")

    # Write the fixed content back
    with open(file_path, "w") as f:
        f.write(new_content)

    print(f"Fixed file written to: {file_path}")


def main():
    """Main function."""
    file_path = "/Volumes/PRO-G40/Code/omnibase_core/tests/unit/models/core/test_model_cli_action.py"

    if not Path(file_path).exists():
        print(f"Error: File {file_path} does not exist!")
        sys.exit(1)

    try:
        fix_cli_action_tests(file_path)
        print("✅ CLI Action tests fixed successfully!")
    except Exception as e:
        print(f"❌ Error fixing tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
