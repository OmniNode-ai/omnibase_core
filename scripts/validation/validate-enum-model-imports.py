#!/usr/bin/env python3
"""
ONEX Enum/Model Import Prevention Hook.

Prevents enums from importing models to avoid circular dependencies
and maintain clean architectural boundaries.

Architectural Principle:
- Enums are pure, standalone definitions
- Enums should NEVER import models
- Models can import enums (one-way dependency)
"""

import re
import sys
from pathlib import Path


def check_enum_model_imports(file_path: Path) -> list[tuple[int, str]]:
    """
    Check if an enum file imports from models.

    Args:
        file_path: Path to the enum file

    Returns:
        List of (line_number, import_statement) tuples for violations
    """
    violations = []

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Patterns to detect model imports
        model_import_patterns = [
            r"from\s+omnibase_core\.models\.",
            r"from\s+\.\.models\.",
            r"from\s+\.models\.",
            r"import\s+omnibase_core\.models\.",
        ]

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Check for model imports
            for pattern in model_import_patterns:
                if re.search(pattern, stripped):
                    violations.append((line_num, stripped))
                    break

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return []

    return violations


def main() -> int:
    """
    Main entry point for the hook.

    Returns:
        0 if no violations found, 1 otherwise
    """
    if len(sys.argv) < 2:
        print("Usage: onex_enum_model_import_prevention.py <file> [<file> ...]")
        return 1

    files_to_check = [Path(f) for f in sys.argv[1:]]
    enum_files = [
        f for f in files_to_check if "/enums/" in str(f) and f.suffix == ".py"
    ]

    if not enum_files:
        return 0

    violations_found = False

    for file_path in enum_files:
        violations = check_enum_model_imports(file_path)

        if violations:
            violations_found = True
            print(f"\n{file_path}:")
            print("  ❌ Enum importing from models (architectural violation)")
            print("\n  Violations:")
            for line_num, import_stmt in violations:
                print(f"    Line {line_num}: {import_stmt}")

    if violations_found:
        print(
            "\n❌ Enums must NEVER import models"
            "\n"
            "\nArchitectural Principle:"
            "\n  - Enums are pure, standalone definitions"
            "\n  - Models can import enums (one-way dependency)"
            "\n  - Enums importing models creates circular dependencies"
            "\n"
            "\nFix:"
            "\n  1. Remove model imports from enum files"
            "\n  2. If enum needs model references, use string literals or TYPE_CHECKING"
            "\n  3. Move model-dependent logic to a separate utility module"
            "\n"
            "\nExamples:"
            "\n  ❌ from omnibase_core.models.core.model_semver import ModelSemVer"
            "\n  ✓  # Reference as string: 'ModelSemVer'"
            "\n  ✓  # Move to utils/enum_model_helpers.py if logic needed"
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
