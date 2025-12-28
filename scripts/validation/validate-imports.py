#!/usr/bin/env python3
"""
Generic import validation for omni* packages.

This tool automatically detects the package structure and validates
that the package can be imported correctly.
"""

import importlib
import sys
from pathlib import Path


class GenericImportValidator:
    """Validates omni* package imports based on discovered structure."""

    def __init__(self, package_name: str | None = None):
        self.results: list[tuple[str, bool, str]] = []

        # Auto-detect package name from repository if not provided
        if package_name is None:
            self.package_name = self._detect_package_name()
        else:
            self.package_name = package_name

        print(f"🎯 {self.package_name} Import Validation")
        print("=" * 40)

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

    def _discover_importable_modules(self) -> list[str]:
        """Discover all importable modules in the package."""
        modules = []
        package_dir = Path(f"src/{self.package_name}")

        if not package_dir.exists():
            return [self.package_name]  # Just test the main package

        # Add main package
        modules.append(self.package_name)

        # Discover submodules
        for py_file in package_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                # Convert path to module name
                rel_path = py_file.parent.relative_to(Path("src"))
                module_name = str(rel_path).replace("/", ".").replace("\\", ".")
                modules.append(module_name)
            elif not py_file.name.startswith("_"):
                # Individual module files
                rel_path = py_file.relative_to(Path("src")).with_suffix("")
                module_name = str(rel_path).replace("/", ".").replace("\\", ".")
                modules.append(module_name)

        return sorted(set(modules))

    def test_import(self, module_name: str) -> bool:
        """Test importing a module."""
        try:
            importlib.import_module(module_name)
            self.results.append((module_name, True, "OK"))
            return True
        except ImportError as e:
            self.results.append((module_name, False, str(e)))
            return False
        except Exception as e:
            self.results.append((module_name, False, f"Unexpected error: {e}"))
            return False

    def validate_core_imports(self) -> bool:
        """Test core package imports."""
        print(f"🔍 Testing {self.package_name} imports...")

        success = True

        # Test main package
        success &= self.test_import(self.package_name)

        # Test key submodules if they exist
        common_submodules = [
            f"{self.package_name}.models",
            f"{self.package_name}.enums",
            f"{self.package_name}.utils",
            f"{self.package_name}.validation",
        ]

        for module in common_submodules:
            module_path = Path("src") / module.replace(".", "/") / "__init__.py"
            if module_path.exists():
                success &= self.test_import(module)

        return success

    def validate_spi_integration(self) -> bool:
        """Test SPI integration if available."""
        print("🔍 Testing omnibase_spi integration...")

        success = True

        try:
            # Test basic SPI imports
            import omnibase_spi.protocols.core
            import omnibase_spi.protocols.types  # noqa: F401

            self.results.append(("SPI Protocol imports", True, "OK"))
            self.results.append(("SPI Types imports", True, "OK"))
        except ImportError as e:
            self.results.append(("SPI Protocol imports", False, str(e)))
            self.results.append(("SPI Types imports", False, str(e)))
            success = False
        except Exception as e:
            self.results.append(("SPI integration", False, f"Unexpected error: {e}"))
            success = False

        return success

    def validate_package_functionality(self) -> bool:
        """Test basic package functionality."""
        print("🔍 Testing container functionality...")

        success = True

        try:
            # Test that we can import and use basic functionality
            pkg = importlib.import_module(self.package_name)

            # Note: No version check - versions come from contracts, not __version__

            self.results.append(
                ("Container functionality", True, "Basic import successful")
            )

        except Exception as e:
            self.results.append(("Container functionality", False, str(e)))
            success = False

        return success

    def print_results(self):
        """Print validation results."""
        print("\n📊 Import Validation Results:")
        print("=" * 50)

        passed = 0
        failed = 0

        for description, success, message in self.results:
            status = "✅" if success else "❌"
            print(f"{status} {description}: {'PASS' if success else 'FAIL'}", end="")
            if not success or message != "OK":
                print(f" - {message}")
            else:
                print()

            if success:
                passed += 1
            else:
                failed += 1

        print(f"\nResults: {passed} passed, {failed} failed")

        if failed > 0:
            print(f"\n🚫 {failed} import issues need to be fixed")
            print("   Check dependencies and installation")
            return False
        else:
            print("\n✅ All imports working correctly!")
            return True


def main():
    """Main validation entry point."""
    validator = GenericImportValidator()

    # Run all validations
    core_ok = validator.validate_core_imports()
    spi_ok = validator.validate_spi_integration()
    functionality_ok = validator.validate_package_functionality()

    # Print results
    success = validator.print_results()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
