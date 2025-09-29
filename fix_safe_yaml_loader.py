#!/usr/bin/env python3
"""
Script to resolve the many ModelErrorContext conflicts in safe_yaml_loader.py
All conflicts follow the same pattern - replace verbose constructor with factory method
"""

import re


def fix_safe_yaml_loader():
    """Fix all ModelErrorContext conflicts in safe_yaml_loader.py"""

    filepath = "/Volumes/PRO-G40/Code/omnibase_core/src/omnibase_core/utils/safe_yaml_loader.py"

    with open(filepath, "r") as f:
        content = f.read()

    # Replace all the verbose ModelErrorContext patterns with the factory method
    # Pattern: Replace entire conflict sections with main's version

    # General pattern for most cases
    pattern1 = r'<<<<<<< HEAD\s*details=ModelErrorContext\(\s*file_path=[^,]*,\s*line_number=None,\s*column_number=None,\s*function_name="[^"]*",\s*module_name=None,\s*stack_trace=None,\s*.*?\).*?\n=======\s*(.*?)\n>>>>>>> origin/main'

    def replace_with_main(match):
        return match.group(1)

    content = re.sub(
        pattern1, replace_with_main, content, flags=re.MULTILINE | re.DOTALL
    )

    # Check if all conflicts are resolved
    if "<<<<<<< HEAD" in content:
        print("Warning: Some conflicts may remain")
        # Show remaining conflicts
        remaining = content.split("<<<<<<< HEAD")
        print(f"Found {len(remaining)-1} remaining conflicts")

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Fixed safe_yaml_loader.py conflicts")

    return "<<<<<<< HEAD" not in content


if __name__ == "__main__":
    success = fix_safe_yaml_loader()
    if success:
        print("All conflicts resolved successfully!")
    else:
        print("Some conflicts remain - manual resolution needed")
