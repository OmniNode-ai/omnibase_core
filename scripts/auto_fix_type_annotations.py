#!/usr/bin/env python3
"""
Automated Type Annotation Fixer - Enhanced Version

This script automatically adds type annotations to functions based on common patterns
observed in the omnibase_core models.

Enhanced to handle:
- Field serializers (@field_serializer)
- Old-style validators (@validator with values parameter)
- Model validators (@model_validator)
- Property methods (@property)
- Functions with **kwargs
- Context managers (__enter__, __exit__)
- Iterator methods (__iter__, __next__)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def run_mypy(paths: List[str]) -> List[Tuple[str, int, str]]:
    """Run mypy and extract no-untyped-def errors."""
    cmd = ["poetry", "run", "mypy"] + paths
    result = subprocess.run(cmd, capture_output=True, text=True)

    errors = []
    # Check both stdout and stderr
    output = result.stdout + result.stderr
    for line in output.split("\n"):
        if "[no-untyped-def]" in line:
            match = re.match(r"^([^:]+):(\d+):\s+error:\s+(.+)\[no-untyped-def\]", line)
            if match:
                filepath, lineno, msg = match.groups()
                errors.append((filepath, int(lineno), msg))

    return errors


def read_file_lines(filepath: str) -> List[str]:
    """Read file into lines."""
    return Path(filepath).read_text().split("\n")


def write_file_lines(filepath: str, lines: List[str]) -> None:
    """Write lines back to file."""
    Path(filepath).write_text("\n".join(lines))


def backup_file(filepath: str) -> None:
    """Create backup of file."""
    path = Path(filepath)
    backup_path = path.with_suffix(path.suffix + ".bak")
    backup_path.write_text(path.read_text())


def ensure_imports(lines: List[str], imports_needed: Set[str]) -> List[str]:
    """Ensure necessary imports are present."""
    # Find imports section
    import_idx = None
    typing_import_idx = None
    typing_extensions_idx = None

    for i, line in enumerate(lines):
        if line.startswith("from typing import"):
            typing_import_idx = i
        elif line.startswith("from typing_extensions import"):
            typing_extensions_idx = i
        elif line.startswith("from pydantic"):
            import_idx = i

    # Handle typing imports
    typing_imports = {"Any", "Iterator", "Self"}
    needed_typing = typing_imports & imports_needed

    if needed_typing:
        if typing_import_idx is not None:
            # Add to existing typing import
            existing_line = lines[typing_import_idx]
            for imp in needed_typing:
                if imp not in existing_line:
                    # Add to import list
                    existing_line = existing_line.replace(
                        "import ", f"import {imp}, "
                    )
            lines[typing_import_idx] = existing_line
        else:
            # Add new typing import
            insert_pos = import_idx if import_idx else 0
            import_str = f"from typing import {', '.join(sorted(needed_typing))}"
            lines.insert(insert_pos, import_str)
            # Update indices
            if import_idx:
                import_idx += 1
            if typing_extensions_idx:
                typing_extensions_idx += 1

    # Handle typing_extensions imports (Self for older Python)
    if "Self" in imports_needed and typing_extensions_idx is None:
        # Check Python version in pyproject.toml or use typing_extensions
        # For safety, use typing_extensions for Self
        pass  # Already handled in typing imports above

    # Handle pydantic_core imports
    if "ValidationInfo" in imports_needed:
        has_pydantic_core = any(
            "from pydantic_core import" in line for line in lines
        )
        if not has_pydantic_core:
            insert_pos = (typing_import_idx + 1) if typing_import_idx else 0
            lines.insert(insert_pos, "from pydantic_core import ValidationInfo")

    return lines


def get_decorator_context(lines: List[str], idx: int, lookback: int = 5) -> str:
    """Get decorator context for a function."""
    start = max(0, idx - lookback)
    context = "\n".join(lines[start:idx])
    return context


def fix_function_at_line(lines: List[str], lineno: int, error_msg: str) -> Tuple[List[str], Set[str]]:
    """Fix function at specific line number."""
    imports_needed: Set[str] = set()
    idx = lineno - 1

    if idx >= len(lines):
        return lines, imports_needed

    line = lines[idx]
    decorator_context = get_decorator_context(lines, idx)

    # Pattern 1: field_serializer
    if "@field_serializer" in decorator_context:
        if "def serialize_" in line and "-> " not in line:
            # Field serializers typically return str | None for masked values
            if "(self, value)" in line:
                lines[idx] = line.replace(
                    "(self, value)",
                    "(self, value: Any) -> str | None"
                )
            elif "(self, value," in line:
                lines[idx] = re.sub(
                    r'\(self, value,([^)]*)\)',
                    r'(self, value: Any, \1) -> str | None',
                    line
                )
            imports_needed.add("Any")
            return lines, imports_needed

    # Pattern 2: Old-style @validator with values parameter
    if "@validator" in decorator_context and "(cls, v, values)" in line:
        if "-> " not in line:
            lines[idx] = line.replace(
                "(cls, v, values)",
                "(cls, v: Any, values: dict[str, Any]) -> Any"
            )
            imports_needed.add("Any")
            return lines, imports_needed

    # Pattern 3: field_validator with info parameter
    if "@field_validator" in decorator_context:
        # Fix validator: def validate_xxx(cls, v, info) -> type:
        if "(cls, v, info)" in line or "(cls, v," in line and "info" in line:
            if "-> " not in line:
                # Determine return type from field name
                return_type = "Any"  # Default to Any for validators

                # Fix the signature
                if "(cls, v, info)" in line:
                    lines[idx] = line.replace(
                        "(cls, v, info)",
                        f"(cls, v: Any, info: ValidationInfo) -> Any"
                    )
                imports_needed.add("Any")
                imports_needed.add("ValidationInfo")
            return lines, imports_needed

        # Fix validator: def validate_xxx(cls, v) -> type:
        elif "(cls, v)" in line and "-> " not in line:
            lines[idx] = line.replace("(cls, v)", "(cls, v: Any) -> Any")
            imports_needed.add("Any")
            return lines, imports_needed

    # Pattern 4: model_validator
    if "@model_validator" in decorator_context:
        if "(cls," in line and "-> " not in line:
            # Model validators return Self
            lines[idx] = re.sub(
                r'\(cls,([^)]*)\)',
                r'(cls, \1) -> Self',
                line
            )
            imports_needed.add("Self")
            return lines, imports_needed

    # Pattern 5: Property methods
    if "@property" in decorator_context:
        if "def " in line and "):" in line and "-> " not in line:
            # Need to infer return type - default to Any
            lines[idx] = line.replace("):", ") -> Any:")
            imports_needed.add("Any")
            return lines, imports_needed

    # Pattern 6: Iterator methods
    if "def __iter__" in line and "-> " not in line:
        lines[idx] = line.replace("):", ") -> Iterator[Any]:")
        imports_needed.add("Iterator")
        imports_needed.add("Any")
        return lines, imports_needed

    if "def __next__" in line and "-> " not in line:
        lines[idx] = line.replace("):", ") -> Any:")
        imports_needed.add("Any")
        return lines, imports_needed

    # Pattern 7: Context managers
    if "def __enter__" in line and "-> " not in line:
        lines[idx] = line.replace("):", ") -> Self:")
        imports_needed.add("Self")
        return lines, imports_needed

    if "def __exit__" in line and "-> " not in line:
        # __exit__ returns None or bool
        lines[idx] = line.replace("):", ") -> None:")
        return lines, imports_needed

    # Pattern 8: classmethod with **kwargs
    if "@classmethod" in decorator_context:
        if "**kwargs)" in line and "**kwargs: Any)" not in line:
            lines[idx] = line.replace("**kwargs)", "**kwargs: Any)")
            imports_needed.add("Any")
            return lines, imports_needed

    # Pattern 9: Functions with unannotated **kwargs
    if "**kwargs)" in line and "**kwargs: Any)" not in line and "-> " not in line:
        # Add kwargs annotation and return type
        lines[idx] = line.replace("**kwargs)", "**kwargs: Any) -> None")
        imports_needed.add("Any")
        return lines, imports_needed

    # Pattern 10: __init__ method
    if "def __init__" in line:
        if "**data)" in line and "-> None" not in line:
            lines[idx] = line.replace("**data)", "**data: Any) -> None")
            imports_needed.add("Any")
            return lines, imports_needed

    # Pattern 11: comparison operators
    if any(f"def {op}" in line for op in ["__eq__", "__lt__", "__le__", "__gt__", "__ge__"]):
        if "other)" in line and "-> bool" not in line:
            lines[idx] = line.replace("other)", "other: object) -> bool")
            return lines, imports_needed

    # Pattern 12: arithmetic operators
    if any(f"def {op}" in line for op in ["__add__", "__sub__", "__mul__", "__truediv__"]):
        if "other)" in line and "-> " not in line:
            # Extract class name
            class_name = None
            for i in range(idx, -1, -1):
                if lines[i].startswith("class "):
                    class_name = lines[i].split("(")[0].replace("class ", "").strip()
                    break
            if class_name:
                lines[idx] = line.replace("other)", f'other: object) -> "{class_name}"')
            return lines, imports_needed

    # Pattern 13: methods missing return type (last resort)
    if "def " in line and "):" in line and "-> " not in line:
        # Check if it's a special method that should return None
        if "def __" in line:
            # Most dunder methods return None unless specifically handled above
            if "def __str__" in line or "def __repr__" in line:
                lines[idx] = line.replace("):", ") -> str:")
            else:
                lines[idx] = line.replace("):", ") -> None:")
        else:
            # Regular method - default to None
            lines[idx] = line.replace("):", ") -> None:")
        return lines, imports_needed

    return lines, imports_needed


def fix_file(filepath: str, errors: List[Tuple[int, str]], backup: bool = False) -> int:
    """Fix all errors in a file."""
    if backup:
        backup_file(filepath)

    lines = read_file_lines(filepath)
    all_imports_needed: Set[str] = set()

    # Sort errors by line number (descending) to avoid index shifts
    errors_sorted = sorted(errors, key=lambda x: x[0], reverse=True)

    for lineno, error_msg in errors_sorted:
        lines, imports_needed = fix_function_at_line(lines, lineno, error_msg)
        all_imports_needed.update(imports_needed)

    # Add necessary imports
    if all_imports_needed:
        lines = ensure_imports(lines, all_imports_needed)

    write_file_lines(filepath, lines)
    return len(errors)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automatically fix type annotation errors in Python files"
    )
    parser.add_argument(
        "--dirs",
        nargs="+",
        help="Directories to process (relative to src/omnibase_core/)",
        default=["models/configuration", "models/contracts", "models/discovery", "models/events"]
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak backups before modifying files"
    )
    args = parser.parse_args()

    # Convert relative paths to absolute
    base_path = Path("src/omnibase_core")
    paths = [str(base_path / d) for d in args.dirs]

    print("🔍 Scanning for untyped functions...")
    print(f"   Directories: {', '.join(args.dirs)}")

    errors = run_mypy(paths)

    if not errors:
        print("✅ No untyped functions found!")
        return 0

    print(f"📝 Found {len(errors)} untyped functions")

    # Group by file
    by_file: Dict[str, List[Tuple[int, str]]] = {}
    for filepath, lineno, error_msg in errors:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append((lineno, error_msg))

    # Fix each file
    total_fixed = 0
    for filepath, file_errors in sorted(by_file.items()):
        print(f"  Fixing {Path(filepath).name} ({len(file_errors)} errors)...", end=" ")
        fixed = fix_file(filepath, file_errors, backup=args.backup)
        total_fixed += fixed
        print(f"✓ {fixed} fixed")

    print(f"\n✅ Fixed {total_fixed} function annotations!")

    # Verify
    print("\n🔍 Verifying fixes...")
    remaining = run_mypy(paths)
    if remaining:
        print(f"⚠️  {len(remaining)} errors remain (may need manual review)")
        print("\nRemaining errors:")
        for filepath, lineno, msg in remaining[:10]:  # Show first 10
            print(f"  {Path(filepath).name}:{lineno} - {msg}")
        if len(remaining) > 10:
            print(f"  ... and {len(remaining) - 10} more")
        return 1
    else:
        print("✅ All type annotation errors fixed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
