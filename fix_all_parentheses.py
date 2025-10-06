#!/usr/bin/env python3
"""
Fix all parentheses issues in the metadata value file.
"""

import re
from pathlib import Path


def fix_parentheses_in_file(file_path: Path):
    """Fix parentheses issues in ModelOnexError statements."""
    content = file_path.read_text()

    # Pattern to match ModelOnexError statements and fix the parentheses
    # We need to find all raise statements and ensure they have proper closing

    # First, let's find all the problematic patterns and fix them
    lines = content.split("\n")
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a ModelOnexError raise statement
        if "raise ModelOnexError(" in line:
            # Start collecting the full statement
            statement_lines = [line]
            j = i + 1

            # Find the end of the statement
            paren_count = line.count("(") - line.count(")")
            while j < len(lines) and paren_count > 0:
                statement_lines.append(lines[j])
                paren_count += lines[j].count("(") - lines[j].count(")")
                j += 1

            # Fix the last line if it has the wrong number of closing parentheses
            if statement_lines:
                last_line = statement_lines[-1]
                # Fix patterns like "})" when it should be "}))"
                if "})" in last_line and not last_line.strip().endswith("})"):
                    # Count opening and closing parentheses in the entire statement
                    full_statement = "\n".join(statement_lines)
                    open_count = full_statement.count("(")
                    close_count = full_statement.count(")")

                    # Add missing closing parentheses
                    missing_parens = open_count - close_count
                    if missing_parens > 0:
                        last_line = last_line.rstrip() + ")" * missing_parens
                        statement_lines[-1] = last_line

                # Fix over-parenthesized statements (too many closing parentheses)
                elif last_line.strip().endswith("})))"):
                    last_line = last_line.replace("})))", "}))")
                    statement_lines[-1] = last_line

            fixed_lines.extend(statement_lines)
            i = j
        else:
            fixed_lines.append(line)
            i += 1

    # Write back if changed
    fixed_content = "\n".join(fixed_lines)
    if fixed_content != content:
        file_path.write_text(fixed_content)
        print(f"Fixed parentheses in {file_path}")
        return True
    return False


if __name__ == "__main__":
    file_path = Path("src/omnibase_core/models/metadata/model_metadata_value.py")
    fix_parentheses_in_file(file_path)
