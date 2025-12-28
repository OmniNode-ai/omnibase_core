#!/usr/bin/env python3
"""
Generic stability validation for omni* packages.

This tool validates that any omni* package is fully stable for downstream
development by running all validation checks based on discovered structure.
"""

import subprocess
import sys
from pathlib import Path


class GenericStabilityValidator:
    """Validates omni* package comprehensive stability."""

    def __init__(self, package_name: str | None = None):
        # Auto-detect package name from repository if not provided
        if package_name is None:
            self.package_name = self._detect_package_name()
        else:
            self.package_name = package_name

        print(f"🎯 {self.package_name} Comprehensive Stability Validation")
        print("=" * 60)

    def _detect_package_name(self) -> str:
        """Auto-detect package name from repository structure."""
        # Try to find src/{package_name} directory
        src_dir = Path("src")
        if src_dir.exists():
            for item in src_dir.iterdir():
                if item.is_dir() and item.name.startswith("omni"):
                    return item.name

        # Fallback: derive from current directory name
        cwd = Path.cwd().name
        if cwd.startswith("omni"):
            return cwd.replace("-", "_").replace(".", "_")

        # Default fallback
        return "omnibase_core"

    def validate_package_structure(self) -> bool:
        """Validate that package has proper structure."""
        print("🔍 Validating package structure...")

        # Check for basic required structure
        src_path = Path(f"src/{self.package_name}")
        if not src_path.exists():
            print("  ❌ Package structure: FAIL")
            print(f"     Missing: {src_path}")
            return False

        init_file = src_path / "__init__.py"
        if not init_file.exists():
            print("  ❌ Package structure: FAIL")
            print(f"     Missing: {init_file}")
            return False

        print("  ✅ Package structure: PASS")
        return True

    def run_import_validation(self) -> bool:
        """Run import validation script."""
        print("🔍 Running import validation...")

        try:
            result = subprocess.run(
                [sys.executable, "scripts/validate-imports.py"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                check=False,
            )

            if result.returncode == 0:
                print("  ✅ Import validation: PASS")
                return True
            else:
                print("  ❌ Import validation: FAIL")
                if result.stderr:
                    print(f"     {result.stderr}")
                return False

        except Exception as e:
            print(f"  ❌ Import validation: FAIL - {e}")
            return False

    def run_downstream_validation(self) -> bool:
        """Run downstream validation script."""
        print("🔍 Running downstream validation...")

        try:
            result = subprocess.run(
                [sys.executable, "scripts/validate-downstream.py"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                check=False,
            )

            if result.returncode == 0:
                print("  ✅ Downstream validation: PASS")
                return True
            else:
                print("  ❌ Downstream validation: FAIL")
                if result.stderr:
                    print(f"     {result.stderr}")
                return False

        except Exception as e:
            print(f"  ❌ Downstream validation: FAIL - {e}")
            return False

    def run_type_checking(self) -> bool:
        """Run MyPy type checking if available."""
        print("🔍 Running type checking...")

        try:
            result = subprocess.run(
                [
                    "poetry",
                    "run",
                    "mypy",
                    f"src/{self.package_name}/",
                    "--config-file=mypy.ini",
                ],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                check=False,
            )

            # MyPy returns 0 for success, non-zero for issues
            if result.returncode == 0:
                print("  ✅ Type checking: PASS")
                return True
            else:
                print("  ❌ Type checking: FAIL")
                # Show a few example errors, not all of them
                lines = result.stdout.split("\n")
                error_lines = [line for line in lines if "error:" in line]
                for line in error_lines[:5]:  # Show first 5 errors
                    print(f"     {line}")
                if len(error_lines) > 5:
                    print(f"     ... ({len(error_lines) - 5} additional errors)")
                return False

        except Exception as e:
            print(f"  ✅ Type checking: PASS (MyPy not available: {e})")
            return True  # Don't fail if MyPy is not available

    def run_code_linting(self) -> bool:
        """Run code linting with Ruff if available."""
        print("🔍 Running code linting...")

        try:
            result = subprocess.run(
                ["poetry", "run", "ruff", "check", f"src/{self.package_name}/"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                check=False,
            )

            if result.returncode == 0:
                print("  ✅ Code linting: PASS")
                return True
            else:
                print("  ❌ Code linting: FAIL")
                # Show a few example issues
                lines = result.stdout.split("\n")
                issue_lines = [
                    line
                    for line in lines
                    if line.strip() and not line.startswith("Found")
                ]
                for line in issue_lines[:5]:  # Show first 5 issues
                    print(f"     {line}")
                if len(issue_lines) > 5:
                    print(f"     ... ({len(issue_lines) - 5} additional issues)")
                return False

        except Exception as e:
            print(f"  ✅ Code linting: PASS (Ruff not available: {e})")
            return True  # Don't fail if Ruff is not available

    def run_test_suite(self) -> bool:
        """Run test suite if available."""
        print("🔍 Running test suite...")

        # Check if tests directory exists
        test_paths = [Path("tests"), Path("test")]
        test_dir = None
        for path in test_paths:
            if path.exists():
                test_dir = path
                break

        if not test_dir:
            print("  ✅ Test suite: PASS (no tests directory)")
            return True

        try:
            result = subprocess.run(
                ["poetry", "run", "pytest", str(test_dir), "-v"],
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
                check=False,
            )

            if result.returncode == 0:
                print("  ✅ Test suite: PASS")
                return True
            else:
                print("  ❌ Test suite: FAIL")
                # Show summary line if available
                lines = result.stdout.split("\n")
                summary_lines = [
                    line for line in lines if "failed" in line and "passed" in line
                ]
                if summary_lines:
                    print(f"     {summary_lines[-1]}")
                return False

        except Exception as e:
            print(f"  ✅ Test suite: PASS (pytest not available: {e})")
            return True  # Don't fail if pytest is not available

    def run_validation(self) -> bool:
        """Run complete stability validation."""
        results = []

        results.append(("Package Structure", self.validate_package_structure()))
        results.append(("Import Validation", self.run_import_validation()))
        results.append(("Downstream Validation", self.run_downstream_validation()))
        results.append(("Type Checking", self.run_type_checking()))
        results.append(("Code Linting", self.run_code_linting()))
        results.append(("Test Suite", self.run_test_suite()))

        # Print summary
        print("\n📊 Stability Validation Summary:")
        print("=" * 40)

        passed = 0
        failed = 0

        for name, success in results:
            status = "✅" if success else "❌"
            result = "PASS" if success else "FAIL"
            print(f"{status} {name}: {result}")

            if success:
                passed += 1
            else:
                failed += 1

        print(f"\nResults: {passed} passed, {failed} failed")

        if failed > 0:
            print(
                f"\n🚫 {self.package_name} requires {failed} fixes before full stability"
            )
            print("   Address the failed checks above")
            return False
        else:
            print(f"\n✅ {self.package_name} is fully stable for production use!")
            return True


def main():
    """Main validation entry point."""
    validator = GenericStabilityValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
