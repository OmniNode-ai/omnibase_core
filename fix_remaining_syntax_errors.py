#!/usr/bin/env python3
"""
Fix all remaining syntax errors in the codebase caused by malformed import statements.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def fix_syntax_errors_in_file(file_path: Path) -> bool:
    """Fix syntax errors in a single file."""
    try:
        content = file_path.read_text()
        original_content = content

        # Fix patterns that cause syntax errors
        patterns_to_fix = [
            # Fix duplicate/empty imports
            (
                r"from typing import TYPE_CHECKING, , AnyAny, Dict, Any, Dict",
                "from typing import TYPE_CHECKING, Any, Dict",
            ),
            (
                r"from typing import .*?, , DictDict",
                lambda m: m.group(0).replace(", , DictDict", ", Dict"),
            ),
            (
                r"from typing import .*?, , DictDict",
                lambda m: m.group(0).replace(", , DictDict", ", Dict"),
            ),
            (
                r"from typing import Any, Callable, , DictDict",
                "from typing import Any, Callable, Dict",
            ),
            (r"from typing import Any, , DictDict", "from typing import Any, Dict"),
            (r", DictDict", ", Dict"),
            (r"AnyAny", "Any"),
            (r"DictDict", "Dict"),
            (r"Dict, Dict", "Dict"),
            (r"Optional, Optional", "Optional"),
            (r"from typing import \(", "from typing import ("),
            (r"\)\s*,\s*\)", ")"),
            (r"\s*,\s*,", ","),
        ]

        # Apply fixes
        for pattern, replacement in patterns_to_fix:
            if callable(replacement):
                content = re.sub(pattern, replacement, content)
            else:
                content = re.sub(pattern, replacement, content)

        # Remove trailing commas in import statements
        content = re.sub(
            r"from typing import \((.*?)\),",
            r"from typing import (\1)",
            content,
            flags=re.DOTALL,
        )

        # Remove empty imports with trailing commas
        content = re.sub(r",\s*\)", ")", content)

        # Write back if changed
        if content != original_content:
            file_path.write_text(content)
            print(f"Fixed syntax errors in {file_path}")
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def find_python_files_with_syntax_errors(root_dir: Path) -> list[Path]:
    """Find Python files with syntax errors."""
    files_with_errors = []

    for py_file in root_dir.rglob("*.py"):
        try:
            with open(py_file, encoding="utf-8") as f:
                content = f.read()

            # Try to compile to check for syntax errors
            compile(content, str(py_file), "exec")
        except SyntaxError:
            files_with_errors.append(py_file)
        except Exception:
            # Ignore other errors (like encoding issues)
            pass

    return files_with_errors


def main():
    """Main function to fix all syntax errors."""
    root_dir = Path("src/omnibase_core")

    print("Finding files with syntax errors...")
    files_with_errors = find_python_files_with_syntax_errors(root_dir)

    if not files_with_errors:
        print("No syntax errors found!")
        return

    print(f"Found {len(files_with_errors)} files with syntax errors")

    fixed_count = 0
    for file_path in files_with_errors:
        if fix_syntax_errors_in_file(file_path):
            fixed_count += 1

    print(f"Fixed syntax errors in {fixed_count} files")


if __name__ == "__main__":
    main()
