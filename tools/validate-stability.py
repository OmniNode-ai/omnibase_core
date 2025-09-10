#!/usr/bin/env python3
"""
Comprehensive stability validation for omnibase_core.

This tool validates that omnibase_core is fully stable for downstream
development by running all validation checks:
1. Import validation
2. Union count compliance
3. Type safety validation
4. SPI dependency resolution
5. Service container functionality
6. Pre-commit hook validation
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def run_import_validation() -> bool:
    """Run import validation script."""
    print("🔍 Running import validation...")

    try:
        result = subprocess.run(
            [sys.executable, "tools/validate-imports.py"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            print("  ✅ Import validation: PASS")
            return True
        else:
            print("  ❌ Import validation: FAIL")
            print(f"     {result.stdout}")
            print(f"     {result.stderr}")
            return False

    except Exception as e:
        print(f"  ❌ Import validation error: {e}")
        return False


def run_downstream_validation() -> bool:
    """Run downstream validation script."""
    print("🔍 Running downstream validation...")

    try:
        result = subprocess.run(
            [sys.executable, "tools/validate-downstream.py"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            print("  ✅ Downstream validation: PASS")
            return True
        else:
            print("  ❌ Downstream validation: FAIL")
            print(f"     {result.stdout}")
            print(f"     {result.stderr}")
            return False

    except Exception as e:
        print(f"  ❌ Downstream validation error: {e}")
        return False


def validate_type_checking() -> bool:
    """Run mypy type checking."""
    print("🔍 Running type checking...")

    try:
        result = subprocess.run(
            ["poetry", "run", "mypy", "src/omnibase_core/", "--ignore-missing-imports"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            print("  ✅ Type checking: PASS")
            return True
        else:
            print("  ❌ Type checking: FAIL")
            # Only show first few lines to avoid flooding
            lines = result.stdout.split("\n")[:10]
            for line in lines:
                if line.strip():
                    print(f"     {line}")
            if len(result.stdout.split("\n")) > 10:
                print("     ... (additional errors truncated)")
            return False

    except Exception as e:
        print(f"  ❌ Type checking error: {e}")
        return False


def validate_linting() -> bool:
    """Run ruff linting."""
    print("🔍 Running code linting...")

    try:
        result = subprocess.run(
            ["poetry", "run", "ruff", "check", "src/omnibase_core/"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            print("  ✅ Code linting: PASS")
            return True
        else:
            print("  ❌ Code linting: FAIL")
            # Only show first few lines
            lines = result.stdout.split("\n")[:10]
            for line in lines:
                if line.strip():
                    print(f"     {line}")
            return False

    except Exception as e:
        print(f"  ❌ Code linting error: {e}")
        return False


def validate_tests() -> bool:
    """Run basic test suite."""
    print("🔍 Running test suite...")

    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode == 0:
            print("  ✅ Test suite: PASS")
            return True
        else:
            print("  ❌ Test suite: FAIL")
            # Show test summary
            lines = result.stdout.split("\n")
            for line in lines:
                if "FAILED" in line or "ERROR" in line or "passed" in line:
                    print(f"     {line}")
            return False

    except Exception as e:
        print(f"  ❌ Test suite error: {e}")
        return False


def validate_package_structure() -> bool:
    """Validate package structure integrity."""
    print("🔍 Validating package structure...")

    required_paths = [
        "src/omnibase_core/__init__.py",
        "src/omnibase_core/core/__init__.py",
        "src/omnibase_core/core/infrastructure_service_bases.py",
        "src/omnibase_core/core/model_onex_container.py",
        "src/omnibase_core/model/__init__.py",
        "src/omnibase_core/enums/__init__.py",
        "pyproject.toml",
        "README.md",
    ]

    missing = []
    for path in required_paths:
        if not Path(path).exists():
            missing.append(path)

    if not missing:
        print("  ✅ Package structure: PASS")
        return True
    else:
        print("  ❌ Package structure: FAIL")
        for path in missing:
            print(f"     Missing: {path}")
        return False


def main() -> int:
    """Main stability validation entry point."""
    print("🎯 omnibase_core Comprehensive Stability Validation")
    print("=" * 60)

    validation_results = []

    # Core validation tests
    validation_results.append(("Package Structure", validate_package_structure()))
    validation_results.append(("Import Validation", run_import_validation()))
    validation_results.append(("Downstream Validation", run_downstream_validation()))
    validation_results.append(("Type Checking", validate_type_checking()))
    validation_results.append(("Code Linting", validate_linting()))
    validation_results.append(("Test Suite", validate_tests()))

    # Print summary
    print("\n📊 Stability Validation Summary:")
    print("=" * 40)

    passed = 0
    failed = 0

    for test_name, success in validation_results:
        if success:
            print(f"✅ {test_name}: PASS")
            passed += 1
        else:
            print(f"❌ {test_name}: FAIL")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 omnibase_core is FULLY STABLE for downstream development!")
        print("   All validation checks passed successfully")
        print("   Ready for production downstream repositories")
        return 0
    else:
        print(f"\n🚫 omnibase_core requires {failed} fixes before full stability")
        print("   Address the failed checks above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
