#!/usr/bin/env python3
"""
Comprehensive import validation for omnibase_core.

This tool systematically tests all critical imports to ensure
downstream repositories can reliably depend on omnibase_core.
"""

import importlib
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ImportValidator:
    """Validates omnibase_core imports systematically."""

    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []

        # Whitelist of allowed import paths to prevent code injection
        self.allowed_imports = {
            # Core package imports
            "omnibase_core",
            # Core infrastructure imports
            "omnibase_core.core.model_onex_container",
            "omnibase_core.core.infrastructure_service_bases",
            # Model imports
            "omnibase_core.model.common.model_typed_value",
            # Enum imports
            "omnibase_core.enums.enum_log_level",
            # Error handling imports
            "omnibase_core.core.errors.core_errors",
            # Event system imports
            "omnibase_core.model.core.model_event_envelope",
            # CLI imports
            "omnibase_core.cli.config",
            # SPI integration imports
            "omnibase_spi.protocols.core",
            "omnibase_spi.protocols.types",
        }

        # Whitelist of allowed import items
        self.allowed_import_items = {
            "ModelONEXContainer",
            "NodeReducerService",
            "NodeComputeService",
            "NodeEffectService",
            "NodeOrchestratorService",
            "ModelValueContainer",
            "StringContainer",
            "EnumLogLevel",
            "OnexError",
            "CoreErrorCode",
            "ModelEventEnvelope",
            "ModelCLIConfig",
            "ProtocolCacheService",
            "ProtocolNodeRegistry",
            "core_types",
        }

    def test_import(self, import_path: str, description: str) -> bool:
        """Test a single import and record result."""
        # Security: Validate import path against whitelist
        if import_path not in self.allowed_imports:
            self.results.append(
                (description, False, f"Import path '{import_path}' not in whitelist")
            )
            return False

        try:
            importlib.import_module(import_path)
            self.results.append((description, True, "OK"))
            return True
        except Exception as e:
            self.results.append((description, False, str(e)))
            return False

    def test_from_import(
        self, from_path: str, import_items: str, description: str
    ) -> bool:
        """Test a from...import statement and record result."""
        # Security: Validate import path against whitelist
        if from_path not in self.allowed_imports:
            self.results.append(
                (description, False, f"Import path '{from_path}' not in whitelist")
            )
            return False

        # Security: Validate import items against whitelist
        items = [item.strip() for item in import_items.split(",")]
        for item in items:
            if item not in self.allowed_import_items:
                self.results.append(
                    (description, False, f"Import item '{item}' not in whitelist")
                )
                return False

        try:
            # Import the module first
            module = importlib.import_module(from_path)

            # Test that each requested item exists in the module
            for item in items:
                if not hasattr(module, item):
                    raise ImportError(f"cannot import name '{item}' from '{from_path}'")

            self.results.append((description, True, "OK"))
            return True
        except Exception as e:
            self.results.append((description, False, str(e)))
            return False

    def validate_all_imports(self) -> bool:
        """Run comprehensive import validation."""
        print("🔍 Testing omnibase_core imports...")

        success = True

        # Core package import
        success &= self.test_import("omnibase_core", "Core package")

        # Core infrastructure imports
        success &= self.test_from_import(
            "omnibase_core.core.model_onex_container",
            "ModelONEXContainer",
            "ONEX Container",
        )

        success &= self.test_from_import(
            "omnibase_core.core.infrastructure_service_bases",
            "NodeReducerService, NodeComputeService, NodeEffectService, NodeOrchestratorService",
            "Service Base Classes",
        )

        # Model imports
        success &= self.test_from_import(
            "omnibase_core.model.common.model_typed_value",
            "ModelValueContainer, StringContainer",
            "Typed Value Models",
        )

        # Enum imports
        success &= self.test_from_import(
            "omnibase_core.enums.enum_log_level", "EnumLogLevel", "Log Level Enum"
        )

        # Error handling imports
        success &= self.test_from_import(
            "omnibase_core.core.errors.core_errors",
            "OnexError, CoreErrorCode",
            "Error Handling",
        )

        # Event system imports
        success &= self.test_from_import(
            "omnibase_core.model.core.model_event_envelope",
            "ModelEventEnvelope",
            "Event Envelope",
        )

        # CLI imports
        success &= self.test_from_import(
            "omnibase_core.cli.config", "ModelCLIConfig", "CLI Config"
        )

        return success

    def validate_spi_integration(self) -> bool:
        """Validate omnibase_spi dependency integration."""
        print("🔍 Testing omnibase_spi integration...")

        success = True

        # Test SPI protocol imports
        try:
            from omnibase_spi.protocols.core import (
                ProtocolCacheService,
                ProtocolNodeRegistry,
            )

            self.results.append(("SPI Protocol imports", True, "OK"))
        except Exception as e:
            self.results.append(("SPI Protocol imports", False, str(e)))
            success = False

        # Test SPI types imports
        try:
            from omnibase_spi.protocols.types import core_types

            self.results.append(("SPI Types imports", True, "OK"))
        except Exception as e:
            self.results.append(("SPI Types imports", False, str(e)))
            success = False

        return success

    def validate_container_functionality(self) -> bool:
        """Test basic container functionality."""
        print("🔍 Testing container functionality...")

        try:
            from omnibase_core.core.model_onex_container import ModelONEXContainer

            # Create container instance
            container = ModelONEXContainer()

            # Test basic container functionality
            # Just test that container creation works

            # Test that container has expected properties
            if hasattr(container, "base_container") and hasattr(
                container, "get_service"
            ):
                self.results.append(("Container functionality", True, "OK"))
                return True
            else:
                self.results.append(
                    ("Container functionality", False, "Missing expected methods")
                )
                return False

        except Exception as e:
            self.results.append(("Container functionality", False, str(e)))
            return False

    def print_results(self) -> Tuple[int, int]:
        """Print validation results and return (passed, failed) counts."""
        print("\n📊 Import Validation Results:")
        print("=" * 50)

        passed = 0
        failed = 0

        for description, success, message in self.results:
            if success:
                print(f"✅ {description}: PASS")
                passed += 1
            else:
                print(f"❌ {description}: FAIL - {message}")
                failed += 1

        return passed, failed


def main() -> int:
    """Main validation entry point."""
    print("🎯 omnibase_core Import Validation")
    print("=" * 40)

    validator = ImportValidator()

    # Run all validations
    import_success = validator.validate_all_imports()
    spi_success = validator.validate_spi_integration()
    container_success = validator.validate_container_functionality()

    # Print results
    passed, failed = validator.print_results()

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 All imports are working correctly!")
        print("   omnibase_core is ready for downstream development")
        return 0
    else:
        print(f"\n🚫 {failed} import issues need to be fixed")
        print("   Check dependencies and installation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
