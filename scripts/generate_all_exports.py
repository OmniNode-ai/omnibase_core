#!/usr/bin/env python3
"""
generate_all_exports.py

Automatically generate __all__ exports for modules with attr-defined errors.
Part of Phase 1: Quick Wins for type safety improvements.

Usage:
    # Dry run (preview changes)
    poetry run python scripts/generate_all_exports.py

    # Apply changes
    poetry run python scripts/generate_all_exports.py --apply

    # Apply changes to specific module
    poetry run python scripts/generate_all_exports.py --apply --module omnibase_core.models.security
"""

import argparse
import ast
import re
import subprocess
from pathlib import Path
from typing import Dict, Set


def extract_public_names(file_path: Path) -> Set[str]:
    """Extract all public class, function, and constant names from a module."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}")
        return set()

    names = set()

    # Walk the AST to find public names
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only include public names (not starting with _)
            if not node.name.startswith("_"):
                names.add(node.name)

        elif isinstance(node, ast.Assign):
            # Include module-level assignments for constants and type aliases
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Include uppercase names (constants) or public names
                    if target.id.isupper() or (
                        not target.id.startswith("_") and target.id not in ("logger",)
                    ):
                        names.add(target.id)

        elif isinstance(node, ast.AnnAssign):
            # Include type annotations at module level
            if isinstance(node.target, ast.Name):
                if node.target.id.isupper() or not node.target.id.startswith("_"):
                    names.add(node.target.id)

    return names


def has_all_declaration(file_path: Path) -> bool:
    """Check if file already has __all__ declaration."""
    try:
        with open(file_path) as f:
            content = f.read()
        return "__all__" in content
    except Exception:
        return False


def add_all_export(file_path: Path, names: Set[str], dry_run: bool = True) -> bool:
    """Add __all__ declaration to module."""
    if not names:
        print(f"⚠️  {file_path.name}: No public names found, skipping")
        return False

    if has_all_declaration(file_path):
        print(f"⚠️  {file_path.name}: __all__ already exists, skipping")
        return False

    # Read current content
    with open(file_path) as f:
        lines = f.readlines()

    # Create __all__ declaration
    sorted_names = sorted(names)
    all_lines = ["__all__ = [\n"]
    for name in sorted_names:
        all_lines.append(f'    "{name}",\n')
    all_lines.append("]\n")

    # Find insertion point (after imports, before first class/function/constant)
    insert_idx = 0
    in_docstring = False
    in_imports = False
    docstring_quotes = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip module docstring
        if i == 0 or (i == 1 and not stripped):
            if '"""' in line or "'''" in line:
                in_docstring = True
                docstring_quotes = '"""' if '"""' in line else "'''"
                # Check if docstring ends on same line
                if line.count(docstring_quotes) >= 2:
                    in_docstring = False
                continue

        if in_docstring:
            if docstring_quotes in line:
                in_docstring = False
            continue

        # Track imports
        if stripped.startswith(("import ", "from ")):
            in_imports = True
            insert_idx = i + 1
            continue

        # After imports, find first non-blank, non-comment line
        if in_imports and stripped and not stripped.startswith("#"):
            insert_idx = i
            # Add blank line before __all__ if needed
            if i > 0 and lines[i - 1].strip():
                all_lines.insert(0, "\n")
            break

    # If no good insertion point found, add after docstring/imports
    if insert_idx == 0:
        insert_idx = len(lines)

    # Insert __all__ declaration
    new_lines = lines[:insert_idx] + all_lines + ["\n"] + lines[insert_idx:]

    if dry_run:
        print(f"✓ {file_path.name}: Would add __all__ with {len(sorted_names)} exports")
        print(
            f"  Exports: {', '.join(sorted_names[:5])}"
            + (" ..." if len(sorted_names) > 5 else "")
        )
        return True
    else:
        # Write back
        with open(file_path, "w") as f:
            f.writelines(new_lines)
        print(f"✅ {file_path.name}: Added __all__ with {len(sorted_names)} exports")
        return True


def get_attr_defined_errors(project_root: Path) -> Dict[str, Set[str]]:
    """Get all attr-defined errors from mypy strict mode."""
    result = subprocess.run(
        ["poetry", "run", "mypy", "src/omnibase_core/", "--strict"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    # Parse errors to find affected modules and missing attributes
    affected_modules: Dict[str, Set[str]] = {}

    for line in result.stdout.split("\n"):
        if "[attr-defined]" in line:
            # Extract module name and attribute
            match = re.search(
                r'Module "([^"]+)" does not explicitly export attribute "([^"]+)"',
                line,
            )
            if match:
                module_name = match.group(1)
                attr_name = match.group(2)

                if module_name not in affected_modules:
                    affected_modules[module_name] = set()
                affected_modules[module_name].add(attr_name)

    return affected_modules


def main():
    parser = argparse.ArgumentParser(
        description="Generate __all__ exports for modules with attr-defined errors"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run)",
    )
    parser.add_argument(
        "--module",
        type=str,
        help="Only process specific module (e.g., omnibase_core.models.security)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    src_root = project_root / "src"

    print("═" * 64)
    print("  Generate __all__ Exports for Type Safety")
    print("═" * 64)
    print()

    # Get attr-defined errors
    print("🔍 Scanning for attr-defined errors...")
    affected_modules = get_attr_defined_errors(project_root)

    if not affected_modules:
        print("✅ No attr-defined errors found!")
        return 0

    print(f"   Found {len(affected_modules)} modules with missing exports")
    print()

    # Filter by module if specified
    if args.module:
        affected_modules = {
            k: v for k, v in affected_modules.items() if k.startswith(args.module)
        }
        if not affected_modules:
            print(f"⚠️  No modules found matching: {args.module}")
            return 1

    # Process each module
    total_processed = 0
    total_exports = 0

    if args.apply:
        print("🛠️  Applying changes...")
    else:
        print("👀 Dry run (use --apply to make changes)...")
    print()

    for module_name, expected_attrs in sorted(affected_modules.items()):
        # Convert module name to file path
        module_path = module_name.replace(".", "/") + ".py"
        file_path = src_root / module_path

        if not file_path.exists():
            print(f"⚠️  {module_name}: File not found at {file_path}")
            continue

        # Extract actual public names from the module
        actual_names = extract_public_names(file_path)

        # Combine with expected attributes from mypy errors
        all_names = actual_names | expected_attrs

        # Add __all__ export
        if add_all_export(file_path, all_names, dry_run=not args.apply):
            total_processed += 1
            total_exports += len(all_names)

    print()
    print("═" * 64)
    if args.apply:
        print(f"✅ Processed {total_processed} modules")
        print(f"   Added {total_exports} exports total")
        print()
        print("Next steps:")
        print("  1. Run mypy: poetry run mypy src/omnibase_core/ --strict")
        print("  2. Run tests: poetry run pytest tests/")
        print("  3. Review: git diff")
        print("  4. Commit: git add -A && git commit -m 'feat: add __all__ exports'")
    else:
        print(f"📋 Would process {total_processed} modules")
        print(f"   Would add {total_exports} exports total")
        print()
        print("To apply changes, run with --apply flag:")
        print("  poetry run python scripts/generate_all_exports.py --apply")

    return 0


if __name__ == "__main__":
    exit(main())
