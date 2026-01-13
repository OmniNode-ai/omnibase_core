# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Example: Using omnibase_core validation tools in other repositories

This example demonstrates how other repositories can integrate and use
the validation tools provided by omnibase_core for ONEX compliance.
"""

import sys
from pathlib import Path

# Import validation tools from omnibase_core
from omnibase_core.validation import (ValidationSuite, validate_all,
                                      validate_architecture,
                                      validate_contracts, validate_patterns,
                                      validate_union_usage)


def example_basic_usage():
    """Example: Basic validation usage."""
    print("🔍 Basic Validation Usage Example")
    print("=" * 50)

    # Validate architecture (one model per file)
    print("\n1. Architecture Validation:")
    arch_result = validate_architecture("src/", max_violations=0)
    print(f"   Status: {'✅ PASSED' if arch_result.success else '❌ FAILED'}")
    print(f"   Files checked: {arch_result.files_checked}")
    print(f"   Violations: {len(arch_result.errors)}")

    # Validate union usage
    print("\n2. Union Usage Validation:")
    union_result = validate_union_usage("src/", max_unions=100, strict=True)
    print(f"   Status: {'✅ PASSED' if union_result.success else '❌ FAILED'}")
    print(f"   Total unions: {union_result.metadata.get('total_unions', 0)}")

    # Validate patterns
    print("\n3. Pattern Validation:")
    pattern_result = validate_patterns("src/", strict=True)
    print(f"   Status: {'✅ PASSED' if pattern_result.success else '❌ FAILED'}")
    print(f"   Issues found: {len(pattern_result.errors)}")

    return arch_result.success and union_result.success and pattern_result.success


def example_comprehensive_validation():
    """Example: Run all validations at once."""
    print("\n🎯 Comprehensive Validation Example")
    print("=" * 50)

    # Run all validations with custom parameters
    results = validate_all("src/", strict=True, max_unions=50, max_violations=0)

    print(f"\nValidation Results ({len(results)} validators):")

    overall_success = True
    for validation_type, result in results.items():
        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"  {validation_type:15} {status}")

        # Show details for failed validations
        if not result.success:
            overall_success = False
            print(f"    └─ {len(result.errors)} issues found")
            # Show first few errors as examples
            for error in result.errors[:3]:
                print(f"       • {error}")
            if len(result.errors) > 3:
                print(f"       • ... and {len(result.errors) - 3} more")

    return overall_success


def example_custom_validation_suite():
    """Example: Using ValidationSuite for custom workflows."""
    print("\n⚙️  Custom Validation Suite Example")
    print("=" * 50)

    # Create custom validation suite
    suite = ValidationSuite()

    # List available validators
    print("\nAvailable validators:")
    for name, info in suite.validators.items():
        print(f"  • {name}: {info['description']}")

    # Run specific validations with custom parameters
    directory = Path("src/")

    print(f"\nRunning custom validation on {directory}:")

    # Architecture validation with zero tolerance
    arch_result = suite.run_validation("architecture", directory, max_violations=0)
    print(f"  Architecture (strict): {'✅' if arch_result.success else '❌'}")

    # Union validation with lower limit
    union_result = suite.run_validation(
        "union-usage",
        directory,
        max_unions=25,
        strict=True,  # Stricter limit
    )
    print(f"  Union usage (strict):  {'✅' if union_result.success else '❌'}")

    return arch_result.success and union_result.success


def example_integration_in_ci():
    """Example: Integration pattern for CI/CD."""
    print("\n🔄 CI/CD Integration Example")
    print("=" * 50)

    def validate_for_ci(strict=True, fail_fast=False):
        """Validation function optimized for CI/CD pipelines."""
        print("Running ONEX validation for CI/CD...")

        # Run validations
        results = validate_all("src/", strict=strict)

        # Collect failures
        failures = []
        for validation_type, result in results.items():
            if not result.success:
                failures.append((validation_type, result))

                if fail_fast:
                    print(f"❌ FAIL FAST: {validation_type} validation failed")
                    return False

        # Report results
        if failures:
            print(f"❌ {len(failures)} validation(s) failed:")
            for validation_type, result in failures:
                print(f"  • {validation_type}: {len(result.errors)} issues")
            return False
        else:
            print("✅ All validations passed")
            return True

    # Example CI usage
    ci_success = validate_for_ci(strict=True, fail_fast=False)
    return ci_success


def example_file_level_validation():
    """Example: Validate individual files."""
    print("\n📄 File-Level Validation Example")
    print("=" * 50)

    # Import file-level validation functions
    from omnibase_core.validation.validator_architecture import \
        validate_one_model_per_file
    from omnibase_core.validation.validator_patterns import \
        validate_patterns_file
    from omnibase_core.validation.validator_types import \
        validate_union_usage_file

    # Find Python files to validate
    src_files = list(Path("src/").rglob("*.py"))[:3]  # Just first 3 for demo

    if not src_files:
        print("No Python files found in src/ directory")
        return True

    print(f"Validating {len(src_files)} sample files:")

    all_passed = True
    for file_path in src_files:
        print(f"\n  📁 {file_path}")

        # Architecture validation (one model per file)
        arch_errors = validate_one_model_per_file(file_path)
        arch_status = "✅" if not arch_errors else "❌"
        print(f"    Architecture: {arch_status}")

        # Union usage validation
        union_count, union_issues, _patterns = validate_union_usage_file(file_path)
        union_status = "✅" if not union_issues else "❌"
        print(f"    Union usage:  {union_status} ({union_count} unions)")

        # Pattern validation
        pattern_issues = validate_patterns_file(file_path)
        pattern_status = "✅" if not pattern_issues else "❌"
        print(f"    Patterns:     {pattern_status}")

        if arch_errors or union_issues or pattern_issues:
            all_passed = False

    return all_passed


def example_custom_repository_validator():
    """Example: Create a custom validator for a specific repository type."""
    print("\n🏗️  Custom Repository Validator Example")
    print("=" * 50)

    def validate_fastapi_service(directory="src/"):
        """Custom validation for FastAPI services."""
        print("Validating FastAPI service...")

        # FastAPI services have specific requirements
        results = {}

        # 1. Strict architecture validation
        results["architecture"] = validate_architecture(directory, max_violations=0)

        # 2. Lower union tolerance (APIs should use specific types)
        results["unions"] = validate_union_usage(directory, max_unions=20, strict=True)

        # 3. Strict patterns (API endpoints need good naming)
        results["patterns"] = validate_patterns(directory, strict=True)

        # 4. Contract validation if contracts exist
        if Path("contracts/").exists():
            results["contracts"] = validate_contracts("contracts/")

        # Report results
        all_passed = True
        for validation_type, result in results.items():
            status = "✅ PASSED" if result.success else "❌ FAILED"
            print(f"  {validation_type:12} {status}")
            if not result.success:
                all_passed = False
                print(f"    └─ {len(result.errors)} issues")

        return all_passed

    def validate_cli_tool(directory="src/"):
        """Custom validation for CLI tools."""
        print("Validating CLI tool...")

        # CLI tools may need more unions for argument parsing
        union_result = validate_union_usage(directory, max_unions=100, strict=False)

        # But should have good architecture
        arch_result = validate_architecture(directory, max_violations=0)

        # And follow patterns
        pattern_result = validate_patterns(directory, strict=True)

        results = {
            "architecture": arch_result,
            "unions": union_result,
            "patterns": pattern_result,
        }

        all_passed = True
        for validation_type, result in results.items():
            status = "✅ PASSED" if result.success else "❌ FAILED"
            print(f"  {validation_type:12} {status}")
            if not result.success:
                all_passed = False

        return all_passed

    # Example usage
    print("\nFastAPI Service Validation:")
    fastapi_result = validate_fastapi_service()

    print("\nCLI Tool Validation:")
    cli_result = validate_cli_tool()

    return fastapi_result and cli_result


def main():
    """Run all validation examples."""
    print("🔍 Omnibase Core Validation Tools - Usage Examples")
    print("=" * 60)
    print("\nThese examples show how other repositories can integrate")
    print("and use omnibase_core validation tools for ONEX compliance.\n")

    # Check if we have a src/ directory to validate
    if not Path("src/").exists():
        print("⚠️  No src/ directory found. Creating a minimal example...")
        print("   In real usage, point validators to your source directory.")

        # For demonstration, we'll create a minimal example
        Path("src/").mkdir(exist_ok=True)
        Path("src/example.py").write_text("# Example Python file")

    examples = [
        ("Basic Usage", example_basic_usage),
        ("Comprehensive Validation", example_comprehensive_validation),
        ("Custom Validation Suite", example_custom_validation_suite),
        ("CI/CD Integration", example_integration_in_ci),
        ("File-Level Validation", example_file_level_validation),
        ("Custom Repository Validators", example_custom_repository_validator),
    ]

    results = []
    for name, example_func in examples:
        try:
            result = example_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Example Results Summary:")

    for name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name:30} {status}")

    overall_success = all(success for _, success in results)
    final_status = (
        "✅ ALL EXAMPLES PASSED" if overall_success else "❌ SOME EXAMPLES FAILED"
    )
    print(f"\n🎯 Overall: {final_status}")

    print("\n💡 Next Steps:")
    print("  1. Install omnibase_core in your repository")
    print("  2. Add validation to your pre-commit hooks")
    print("  3. Integrate with your CI/CD pipeline")
    print("  4. Create custom validators for your specific needs")

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
