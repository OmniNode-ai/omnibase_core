#!/usr/bin/env python3
"""Fix misplaced imports that were inserted inside class bodies."""

import re
from pathlib import Path


def fix_file(file_path: Path) -> tuple[bool, str]:
    """
    Fix misplaced imports in a Python file.

    Returns: tuple of (was_modified, error_message)
    """
    try:
        content = file_path.read_text()
        original_content = content

        # Pattern 1: Find imports that appear after class definitions (inside class body)
        # Look for: class declaration followed by import statement
        pattern = r'(class\s+\w+[^:]*:\s*"""[^"]*""")\s*(from\s+[\w.]+\s+import\s+[\w, ]+)\s*\n'

        imports_to_move = []

        # Find all misplaced imports
        for match in re.finditer(pattern, content):
            import_stmt = match.group(2)
            imports_to_move.append(import_stmt)

        if not imports_to_move:
            # Try another pattern: class definition with simpler docstring
            pattern2 = (
                r"(class\s+\w+[^:]*:)\s*\n\s*(from\s+[\w.]+\s+import\s+[\w, ]+)\s*\n"
            )
            for match in re.finditer(pattern2, content):
                import_stmt = match.group(2).strip()
                imports_to_move.append(import_stmt)

        if not imports_to_move:
            return False, ""

        # Remove the misplaced imports from their current location
        for import_stmt in imports_to_move:
            # Remove from inside class (various patterns)
            content = re.sub(rf"\n\s*{re.escape(import_stmt)}\s*\n", "\n", content)

        # Find the last import statement at the top of the file
        lines = content.split("\n")
        last_import_idx = -1

        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                last_import_idx = i

        if last_import_idx == -1:
            # No imports found, add after __future__ or at top
            for i, line in enumerate(lines):
                if line.strip().startswith("from __future__"):
                    last_import_idx = i
                    break

        # Insert the imports after the last import
        if last_import_idx >= 0:
            # Add imports we found
            insert_position = last_import_idx + 1
            for import_stmt in reversed(imports_to_move):
                if import_stmt not in "\n".join(
                    lines
                ):  # Don't add if already exists at top
                    lines.insert(insert_position, import_stmt)

        content = "\n".join(lines)

        # Clean up any duplicate blank lines
        content = re.sub(r"\n\n\n+", "\n\n", content)

        if content != original_content:
            file_path.write_text(content)
            return True, ""

        return False, ""

    except Exception as e:
        return False, str(e)


def main():
    """Find and fix all Python files with syntax errors."""
    fixed_count = 0
    error_count = 0

    # Get all modified Python files
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / "src" / "omnibase_core" / "models"
    mixins_dir = base_dir / "src" / "omnibase_core" / "mixins"

    all_files: list[Path] = []
    all_files.extend(models_dir.rglob("*.py"))
    all_files.extend(mixins_dir.rglob("*.py"))

    for file_path in all_files:
        # Check if file has syntax errors first
        try:
            compile(file_path.read_text(), str(file_path), "exec")
            continue  # No syntax error, skip
        except SyntaxError:
            pass  # Has syntax error, try to fix

        was_modified, error = fix_file(file_path)

        if error:
            print(f"❌ Error fixing {file_path.relative_to(base_dir)}: {error}")
            error_count += 1
        elif was_modified:
            print(f"✅ Fixed {file_path.relative_to(base_dir)}")
            fixed_count += 1

    print(f"\nSummary: Fixed {fixed_count} files, {error_count} errors")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    exit(main())
