#!/usr/bin/env python3
"""
Fix missing Any imports in Python files.
"""

import re
import sys
from pathlib import Path


def fix_any_imports(file_path: Path) -> bool:
    """Fix missing Any imports in a Python file."""
    content = file_path.read_text()

    # Check if Any is used but not imported
    if re.search(r"\bAny\b", content):
        # Check if Any is already imported
        if not re.search(r"from typing import.*\bAny\b", content) and not re.search(
            r"import.*\bAny\b", content
        ):
            # Find the typing import line
            typing_match = re.search(
                r"^from typing import (.*)$", content, re.MULTILINE
            )
            if typing_match:
                # Add Any to existing typing import
                imports = typing_match.group(1)
                if "Any" not in imports:
                    new_imports = (
                        f"Any, {imports}" if not imports.startswith("Any") else imports
                    )
                    content = content.replace(
                        typing_match.group(0), f"from typing import {new_imports}"
                    )
                    file_path.write_text(content)
                    return True
            else:
                # Add new typing import with Any
                # Find a good place to insert it (after __future__ imports if any)
                lines = content.split("\n")
                insert_index = 0

                # Skip docstring and __future__ imports
                for i, line in enumerate(lines):
                    if line.strip().startswith("from __future__"):
                        insert_index = i + 1
                    elif line.strip().startswith('"""') or line.strip().startswith(
                        "'''"
                    ):
                        # Skip multiline docstrings
                        quote = '"""' if line.strip().startswith('"""') else "'''"
                        if line.count(quote) == 1:  # Opening quote only
                            for j in range(i + 1, len(lines)):
                                if quote in lines[j]:
                                    insert_index = j + 1
                                    break
                        else:
                            insert_index = i + 1
                    elif line.strip() and not line.strip().startswith("#"):
                        break

                lines.insert(insert_index, "from typing import Any")
                if insert_index > 0 and lines[insert_index - 1].strip():
                    lines.insert(insert_index, "")  # Add blank line

                content = "\n".join(lines)
                file_path.write_text(content)
                return True

    return False


def main():
    """Fix Any imports in all Python files in src/omnibase_core."""
    src_path = Path("src/omnibase_core")
    fixed_files = []

    for py_file in src_path.rglob("*.py"):
        if fix_any_imports(py_file):
            fixed_files.append(py_file)
            print(f"Fixed Any import in: {py_file}")

    print(f"\nFixed {len(fixed_files)} files")
    for file in fixed_files:
        print(f"  - {file}")


if __name__ == "__main__":
    main()
