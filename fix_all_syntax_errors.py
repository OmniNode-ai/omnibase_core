#!/usr/bin/env python3
"""
Comprehensive fix for all syntax errors after class extraction.
"""

import re
from pathlib import Path


def fix_syntax_errors_in_file(filepath: Path) -> bool:
    """Fix syntax errors in a single file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix all known syntax error patterns
        patterns_to_fix = [
            # Fix typing imports with duplicates
            (
                r"from typing import TYPE_CHECKING, , AnyAny, Dict, Any, Dict",
                "from typing import TYPE_CHECKING, Any, Dict",
            ),
            (
                r"from typing import TYPE_CHECKING, , AnyAny, Any",
                "from typing import TYPE_CHECKING, Any",
            ),
            (
                r"from typing import TYPE_CHECKING, , AnyAny, Dict, Any, Dict, Optional",
                "from typing import TYPE_CHECKING, Any, Dict, Optional",
            ),
            (
                r"from typing import TYPE_CHECKING, , AnyAny, Generic, TypeVar, Any, Optional",
                "from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar",
            ),
            (
                r"from typing import TYPE_CHECKING, , AnyAny, Dict, Any, Optional",
                "from typing import TYPE_CHECKING, Any, Dict, Optional",
            ),
            # Fix duplicate imports in general
            (
                r"from typing import ([^,\n]+), ([^,\n]+), \2",
                r"from typing import \1, \2",
            ),
            (
                r"from typing import ([^,\n]+), ([^,\n]+), ([^,\n]+), \2",
                r"from typing import \1, \2, \3",
            ),
            # Fix broken imports with commas
            (
                r"from typing import TYPE_CHECKING, ,",
                "from typing import TYPE_CHECKING,",
            ),
            (
                r"from typing import TYPE_CHECKING, ([^,]+), ,",
                r"from typing import TYPE_CHECKING, \1,",
            ),
            (
                r"from typing import TYPE_CHECKING, ([^,]+), ([^,]+), ,",
                r"from typing import TYPE_CHECKING, \1, \2,",
            ),
            # Fix AnyAny pattern
            (r"AnyAny", "Any"),
            # Fix duplicate Dict
            (r"Dict, Dict", "Dict"),
            # Fix duplicate Optional
            (r"Optional, Optional", "Optional"),
            # Fix duplicate Any
            (r"Any, Any", "Any"),
        ]

        for pattern, replacement in patterns_to_fix:
            content = re.sub(pattern, replacement, content)

        # Write back if changed
        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"Error fixing syntax errors in {filepath}: {e}")
        return False


def main():
    """Main function to fix all syntax errors."""
    root_dir = Path("src/omnibase_core")

    # Find all Python files
    python_files = list(root_dir.rglob("*.py"))
    print(f"Found {len(python_files)} Python files")

    # Fix syntax errors in each file
    fixed_files = []
    for filepath in python_files:
        if fix_syntax_errors_in_file(filepath):
            fixed_files.append(filepath)
            print(f"Fixed syntax errors in {filepath}")

    print(f"Fixed {len(fixed_files)} files")


if __name__ == "__main__":
    main()
