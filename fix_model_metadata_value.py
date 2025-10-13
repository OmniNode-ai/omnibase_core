#!/usr/bin/env python3
"""
Fix missing parentheses in ModelOnexError statements.
"""

import re
from pathlib import Path


def fix_missing_parentheses(file_path: Path):
    """Fix missing closing parentheses in ModelOnexError statements."""
    content = file_path.read_text()

    # Pattern to find ModelOnexError statements with missing closing parentheses
    # This is a more comprehensive fix for the pattern we've been seeing
    pattern = r"(raise ModelOnexError\([^}]+\}\))\s*(?!$)"

    # Check for the pattern where we have a closing brace but no final closing parenthesis
    lines = content.split("\n")
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if this line ends with '})' - if not, we need to add it
        if "raise ModelOnexError(" in line and i > 0:
            # Look backwards to find the start of the raise statement
            start_idx = i
            while start_idx >= 0 and "raise ModelOnexError(" not in lines[start_idx]:
                start_idx -= 1

            if start_idx >= 0:
                # Find the end of this raise statement
                end_idx = i
                found_end = False

                while end_idx < len(lines):
                    if "})" in lines[end_idx]:
                        # Check if this is properly closed
                        if lines[end_idx].strip().endswith("})"):
                            found_end = True
                            break
                        # If it has '})' but not at the end, we need to add closing parenthesis
                        if "})" in lines[end_idx]:
                            lines[end_idx] = lines[end_idx].replace("})", "}))")
                            found_end = True
                            break
                    end_idx += 1

                # If we didn't find a properly closed statement, add the missing parenthesis
                if not found_end and end_idx < len(lines):
                    lines[end_idx - 1] = lines[end_idx - 1].replace("})", "}))")

        fixed_lines.append(line)
        i += 1

    # Write back if changed
    fixed_content = "\n".join(fixed_lines)
    if fixed_content != content:
        file_path.write_text(fixed_content)
        print(f"Fixed missing parentheses in {file_path}")
        return True
    return False


if __name__ == "__main__":
    file_path = Path("src/omnibase_core/models/metadata/model_metadata_value.py")
    fix_missing_parentheses(file_path)
