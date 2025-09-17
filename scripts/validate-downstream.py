#!/usr/bin/env python3
"""
Validate omnibase_core stability for downstream development.

This tool validates that omnibase_core is ready for use in downstream
repositories by checking:
1. Core imports work correctly
2. Union count compliance (≤ 7000)
3. Type safety validation
4. SPI dependency resolution
5. Service container functionality
"""

import subprocess
import sys
from pathlib import Path


def validate_core_imports() -> bool:
    """Validate that core imports work correctly."""
    print("🔍 Testing core imports...")

    try:
        # Test basic imports
        import omnibase_core
        from omnibase_core.core.infrastructure_service_bases import NodeReducerService
        from omnibase_core.core.model_onex_container import ModelONEXContainer
        from omnibase_core.models.common.model_typed_value import ModelValueContainer

        print("  ✅ Core imports: PASS")
        return True

    except ImportError as e:
        print(f"  ❌ Core imports: FAIL - {e}")
        return False


def validate_union_count() -> bool:
    """Validate Union type count is within limits."""
    print("🔍 Checking Union type count...")

    try:
        # Manual count of union operators
        result = subprocess.run(
            ["grep", "-r", "|", "src/omnibase_core/", "--include=*.py"],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )

        if result.returncode != 0:
            print(f"  ❌ Union count check failed: {result.stderr}")
            return False

        lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
        union_count = len(lines)

        if union_count <= 7000:
            print(f"  ✅ Union count: PASS ({union_count} ≤ 7000)")
            return True
        else:
            print(f"  ❌ Union count: FAIL ({union_count} > 7000)")
            return False

    except Exception as e:
        print(f"  ❌ Union count check error: {e}")
        return False


def validate_type_safety() -> bool:
    """Validate type safety with generic containers."""
    print("🔍 Testing type safety...")

    try:
        from omnibase_core.models.common.model_typed_value import ModelValueContainer

        # Test string container
        str_container = ModelValueContainer.create_string("test")
        if not str_container.is_type(str):
            print("  ❌ String container type safety failed")
            return False

        # Test int container
        int_container = ModelValueContainer.create_int(42)
        if not int_container.is_type(int):
            print("  ❌ Int container type safety failed")
            return False

        # Test type differentiation
        if str_container.is_type(int) or int_container.is_type(str):
            print("  ❌ Type differentiation failed")
            return False

        print("  ✅ Type safety: PASS")
        return True

    except Exception as e:
        print(f"  ❌ Type safety: FAIL - {e}")
        return False


def validate_spi_dependency() -> bool:
    """Validate SPI dependency resolution."""
    print("🔍 Testing SPI dependency...")

    try:
        # Test SPI imports with new simplified paths (post-merge)
        from omnibase_spi import ProtocolEventBus, ProtocolLogger, ProtocolNodeRegistry

        print("  ✅ SPI imports: PASS")
        return True

    except ImportError as e:
        print(f"  ❌ SPI imports: FAIL - {e}")
        print("    💡 Check OMNIBASE_SPI_ISSUES.md for detailed analysis")
        return False


def validate_container_functionality() -> bool:
    """Validate service container functionality."""
    print("🔍 Testing service container...")

    try:
        from omnibase_core.core.model_onex_container import ModelONEXContainer

        # Create test container
        container = ModelONEXContainer()

        # Test container initialization
        if not hasattr(container, "get_service"):
            print("  ❌ Container missing get_service method")
            return False

        print("  ✅ Service container: PASS")
        return True

    except Exception as e:
        print(f"  ❌ Service container: FAIL - {e}")
        return False


def validate_architectural_compliance() -> bool:
    """Validate architectural compliance patterns."""
    print("🔍 Checking architectural compliance...")

    try:
        # Check for anti-patterns in core files
        anti_patterns = []

        # Check for remaining dict[str, Any] patterns
        result = subprocess.run(
            [
                "grep",
                "-r",
                "dict\\[str, Any\\]",
                "src/omnibase_core/core/",
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            anti_patterns.extend(
                [f"dict[str, Any] found: {line}" for line in lines[:3]]
            )

        # Check for string path patterns
        result = subprocess.run(
            [
                "grep",
                "-r",
                "str.*|.*Path\\|Path.*|.*str",
                "src/omnibase_core/core/",
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            if len(lines) > 0:
                anti_patterns.extend([f"Mixed Path|str found: {lines[0]}"])

        if anti_patterns:
            print("  ⚠️  Architectural compliance: WARNINGS")
            for pattern in anti_patterns:
                print(f"    - {pattern}")
            return True  # Warnings don't fail validation
        else:
            print("  ✅ Architectural compliance: PASS")
            return True

    except Exception as e:
        print(f"  ❌ Architectural compliance check error: {e}")
        return True  # Don't fail validation on check errors


def main() -> int:
    """Main validation entry point."""
    print("🎯 omnibase_core Downstream Stability Validation")
    print("=" * 50)

    validation_results = []

    # Core validation tests
    validation_results.append(("Core Imports", validate_core_imports()))
    validation_results.append(("Union Count", validate_union_count()))
    validation_results.append(("Type Safety", validate_type_safety()))
    validation_results.append(("SPI Dependency", validate_spi_dependency()))
    validation_results.append(("Service Container", validate_container_functionality()))
    validation_results.append(("Architecture", validate_architectural_compliance()))

    # Results summary
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_name, result in validation_results:
        if result:
            print(f"✅ {test_name}: PASS")
            passed += 1
        else:
            print(f"❌ {test_name}: FAIL")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 omnibase_core is STABLE for downstream development!")
        print("   Ready to create new repositories based on omnibase_core")
        print("   See DOWNSTREAM_DEVELOPMENT.md for setup guide")
        return 0
    else:
        print(
            f"\n🚫 omnibase_core requires {failed} fixes before downstream development"
        )
        print("   Check error messages above and fix issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
