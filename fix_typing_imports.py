#!/usr/bin/env python3
"""
Fix malformed typing imports across the codebase.

This script targets specific issues found in mypy output:
1. DictDict -> Dict
2. TypedDict import issues
3. Missing typing imports
"""

import os
import re
from pathlib import Path
from typing import Set

# Define the project root
PROJECT_ROOT = Path("/Volumes/PRO-G40/Code/omnibase_core")
SRC_DIR = PROJECT_ROOT / "src" / "omnibase_core"


def fix_typing_imports(content: str) -> str:
    """Fix malformed typing imports."""
    # Fix DictDict -> Dict
    content = re.sub(
        r"from typing import .*?DictDict",
        lambda m: m.group(0).replace("DictDict", "Dict"),
        content,
    )
    content = re.sub(r"DictDict", "Dict", content)

    # Fix TypedDict import issues
    if (
        "TypedDict" in content
        and "from typing_extensions import TypedDict" not in content
        and "from typing import TypedDict" not in content
    ):
        # Add TypedDict import if it's used but not imported
        if "from typing import" in content:
            content = re.sub(
                r"from typing import (.+)",
                lambda m: (
                    f"from typing import {m.group(1)}, TypedDict"
                    if "TypedDict" not in m.group(1)
                    else m.group(0)
                ),
                content,
            )
        else:
            # Add new import line
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from __future__ import"):
                    lines.insert(i + 1, "from typing import TypedDict")
                    break
                if (
                    line.strip()
                    and not line.startswith("#")
                    and not line.startswith("from")
                    and not line.startswith("import")
                ):
                    lines.insert(i, "from typing import TypedDict")
                    break
            content = "\n".join(lines)

    # Fix Task import issue (typing.Task doesn't exist)
    content = re.sub(
        r"from typing import .*?Task", lambda m: m.group(0).replace("Task", ""), content
    )
    content = re.sub(r"Task", "", content)

    return content


def process_file(file_path: Path) -> bool:
    """Process a single file."""
    if not file_path.exists():
        return False

    print(f"Processing {file_path.relative_to(PROJECT_ROOT)}")

    # Read the file
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    # Fix typing imports
    original_content = content
    content = fix_typing_imports(content)

    # Write back if changed
    if content != original_content:
        try:
            file_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False

    return False


def process_python_files(directory: Path) -> int:
    """Process all Python files in a directory."""
    processed_count = 0

    for py_file in directory.rglob("*.py"):
        if py_file.is_file():
            if process_file(py_file):
                processed_count += 1

    return processed_count


def main():
    """Main function."""
    print("Fixing typing imports across the codebase...")

    # Process all Python files in src directory
    processed = process_python_files(SRC_DIR)

    print(f"Processed {processed} files")


if __name__ == "__main__":
    main()
