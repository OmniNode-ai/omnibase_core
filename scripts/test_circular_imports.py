#!/usr/bin/env python3
"""
Comprehensive Circular Import Test

Tests all Python modules in the codebase for circular import issues.
"""

import importlib
import sys
from pathlib import Path


def test_circular_imports(src_path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Test all Python modules for circular imports.

    Args:
        src_path: Path to the source directory

    Returns:
        Tuple of (successful_imports, failed_imports)
    """
    successful = []
    failed = []

    # Find all Python files
    python_files = list(src_path.rglob("*.py"))

    print(f"Found {len(python_files)} Python files to test")
    print("=" * 80)

    for py_file in python_files:
        # Skip __pycache__ and archived files
        if "__pycache__" in str(py_file) or "/archived/" in str(py_file):
            continue

        # Convert file path to module name
        relative_path = py_file.relative_to(src_path)
        module_name = str(relative_path).replace("/", ".").replace(".py", "")

        # Skip __init__ modules for now (test them via their packages)
        if module_name.endswith(".__init__"):
            module_name = module_name[:-9]  # Remove .__init__

        # Skip if module name is empty
        if not module_name or module_name == "__init__":
            continue

        try:
            # Clear any previously imported modules to get a fresh test
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Attempt to import
            importlib.import_module(module_name)
            successful.append(module_name)
            print(f"✓ {module_name}")

        except ImportError as e:
            error_msg = str(e)
            # Check if it's a circular import
            if "circular import" in error_msg.lower():
                failed.append((module_name, error_msg))
                print(f"✗ {module_name}")
                print(f"  Circular import detected: {error_msg}")
            else:
                # Other import errors (missing dependencies, etc.)
                print(f"⚠ {module_name}")
                print(f"  Import error (non-circular): {error_msg[:100]}")

        except Exception as e:
            # Unexpected errors
            print(f"⚠ {module_name}")
            print(f"  Unexpected error: {e!r}")

    return successful, failed


def main() -> int:
    """Run circular import tests and return exit code."""
    # Get the source directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    src_path = project_root / "src"

    if not src_path.exists():
        print(f"Error: Source path not found: {src_path}")
        return 1

    print("Testing for circular imports...")
    print(f"Source path: {src_path}")
    print("")

    successful, failed = test_circular_imports(src_path)

    print("")
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"✓ Successful imports: {len(successful)}")
    print(f"✗ Circular imports detected: {len(failed)}")

    if failed:
        print("")
        print("CIRCULAR IMPORT FAILURES:")
        print("-" * 80)
        for module_name, error_msg in failed:
            print(f"  • {module_name}")
            print(f"    {error_msg}")
        print("")
        return 1

    print("")
    print("🎉 No circular imports detected!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
