#!/usr/bin/env python3
"""
MixinDiscovery API Usage Examples.

Demonstrates how to use the MixinDiscovery API for autonomous code generation,
intelligent mixin composition, and compatibility checking.

Run with: poetry run python examples/mixin_discovery_usage.py
"""

from omnibase_core.mixins.mixin_discovery import MixinDiscovery


def example_1_list_all_mixins() -> None:
    """Example 1: Discover all available mixins."""
    print("=" * 80)
    print("Example 1: List All Available Mixins")
    print("=" * 80)

    discovery = MixinDiscovery()
    all_mixins = discovery.get_all_mixins()

    print(f"\nFound {len(all_mixins)} available mixins:\n")
    for mixin in all_mixins:
        print(f"  • {mixin.name} (v{mixin.version})")
        print(f"    Category: {mixin.category}")
        print(f"    Description: {mixin.description}")
        print(f"    Dependencies: {len(mixin.requires)}")
        print()


def example_2_browse_by_category() -> None:
    """Example 2: Browse mixins by category."""
    print("=" * 80)
    print("Example 2: Browse Mixins by Category")
    print("=" * 80)

    discovery = MixinDiscovery()
    categories = discovery.get_categories()

    print(f"\nAvailable categories: {', '.join(categories)}\n")

    for category in categories:
        mixins = discovery.get_mixins_by_category(category)
        print(f"\n{category.upper()} ({len(mixins)} mixins):")
        for mixin in mixins:
            print(f"  • {mixin.name}: {mixin.description}")


def example_3_check_compatibility() -> None:
    """Example 3: Find compatible mixins for a base composition."""
    print("=" * 80)
    print("Example 3: Check Mixin Compatibility")
    print("=" * 80)

    discovery = MixinDiscovery()

    # Start with MixinRetry as base
    base_mixins = ["MixinRetry"]

    print(f"\nBase composition: {base_mixins}\n")
    print("Finding compatible mixins...\n")

    compatible = discovery.find_compatible_mixins(base_mixins)

    print(f"Found {len(compatible)} compatible mixins:")
    for mixin in compatible[:5]:  # Show first 5
        print(f"  • {mixin.name}")
        print(f"    Category: {mixin.category}")
        print("    Why compatible: No conflicting incompatibilities")
        print()


def example_4_dependency_resolution() -> None:
    """Example 4: Resolve mixin dependencies."""
    print("=" * 80)
    print("Example 4: Dependency Resolution")
    print("=" * 80)

    discovery = MixinDiscovery()

    # Get dependencies for MixinRetry
    mixin_name = "MixinRetry"
    print(f"\nResolving dependencies for {mixin_name}...\n")

    deps = discovery.get_mixin_dependencies(mixin_name)

    print(f"Found {len(deps)} dependencies (in order):")
    for i, dep in enumerate(deps, 1):
        print(f"  {i}. {dep}")


def example_5_validate_composition() -> None:
    """Example 5: Validate a mixin composition."""
    print("=" * 80)
    print("Example 5: Validate Mixin Composition")
    print("=" * 80)

    discovery = MixinDiscovery()

    # Valid composition
    valid_composition = ["MixinRetry", "MixinHealthCheck"]
    print(f"\nValidating composition: {valid_composition}")

    is_valid, errors = discovery.validate_composition(valid_composition)

    if is_valid:
        print("✓ Composition is valid!")
    else:
        print("✗ Composition has errors:")
        for error in errors:
            print(f"  - {error}")

    # Invalid composition with unknown mixin
    print("\n" + "-" * 40)
    invalid_composition = ["MixinRetry", "UnknownMixin"]
    print(f"\nValidating composition: {invalid_composition}")

    is_valid, errors = discovery.validate_composition(invalid_composition)

    if is_valid:
        print("✓ Composition is valid!")
    else:
        print("✗ Composition has errors:")
        for error in errors:
            print(f"  - {error}")


def example_6_intelligent_composition() -> None:
    """Example 6: Intelligent mixin composition workflow."""
    print("=" * 80)
    print("Example 6: Intelligent Mixin Composition Workflow")
    print("=" * 80)

    discovery = MixinDiscovery()

    # Scenario: Build a resilient API client node
    print("\nScenario: Building a resilient API client node")
    print("Requirements:")
    print("  • Automatic retry on transient failures")
    print("  • Health monitoring for the API endpoint")
    print("\nStep-by-step composition:\n")

    # Step 1: Start with retry capability
    composition = ["MixinRetry"]
    print(f"1. Base composition: {composition}")

    # Step 2: Find compatible mixins
    compatible = discovery.find_compatible_mixins(composition)
    print(f"   Found {len(compatible)} compatible mixins")

    # Step 3: Add health check capability
    health_check_mixin = next(
        (m for m in compatible if m.name == "MixinHealthCheck"), None
    )
    if health_check_mixin:
        composition.append(health_check_mixin.name)
        print(f"\n2. Added {health_check_mixin.name}")
        print(f"   Category: {health_check_mixin.category}")

    # Step 4: Validate final composition
    print("\n3. Validating final composition...")
    is_valid, errors = discovery.validate_composition(composition)

    if is_valid:
        print("   ✓ Composition is valid!")
        print(f"\nFinal composition: {' + '.join(composition)}")

        # Show all dependencies
        print("\nAll dependencies required:")
        all_deps = set()
        for mixin_name in composition:
            deps = discovery.get_mixin_dependencies(mixin_name)
            all_deps.update(deps)

        for dep in sorted(all_deps):
            print(f"  • {dep}")
    else:
        print("   ✗ Composition has errors:")
        for error in errors:
            print(f"     - {error}")


def example_7_mixin_details() -> None:
    """Example 7: Inspect mixin details."""
    print("=" * 80)
    print("Example 7: Detailed Mixin Information")
    print("=" * 80)

    discovery = MixinDiscovery()

    mixin_name = "MixinRetry"
    mixin = discovery.get_mixin(mixin_name)

    print(f"\nDetailed information for {mixin_name}:")
    print(f"\n  Name: {mixin.name}")
    print(f"  Version: {mixin.version}")
    print(f"  Category: {mixin.category}")
    print(f"  Description: {mixin.description}")

    print(f"\n  Dependencies ({len(mixin.requires)}):")
    for dep in mixin.requires:
        print(f"    • {dep}")

    print(f"\n  Compatible with ({len(mixin.compatible_with)}):")
    for compat in mixin.compatible_with:
        print(f"    • {compat}")

    if mixin.incompatible_with:
        print(f"\n  Incompatible with ({len(mixin.incompatible_with)}):")
        for incompat in mixin.incompatible_with:
            print(f"    • {incompat}")

    if mixin.config_schema:
        print(f"\n  Configuration schema ({len(mixin.config_schema)} options):")
        for key, schema in list(mixin.config_schema.items())[:3]:  # Show first 3
            print(f"    • {key}:")
            print(f"        type: {schema.get('type', 'unknown')}")
            print(f"        default: {schema.get('default', 'none')}")

    if mixin.usage_examples:
        print(f"\n  Usage examples ({len(mixin.usage_examples)}):")
        for example in mixin.usage_examples[:3]:  # Show first 3
            print(f"    • {example}")


def example_8_code_generation_context() -> None:
    """Example 8: Gather information for code generation."""
    print("=" * 80)
    print("Example 8: Code Generation Context")
    print("=" * 80)

    discovery = MixinDiscovery()

    # Target composition for an API client node
    composition = ["MixinRetry", "MixinHealthCheck"]

    print("\nGenerating code context for node composition:")
    print(f"Target composition: {' + '.join(composition)}\n")

    # Collect all information needed for code generation
    code_context = {
        "mixins": [],
        "all_dependencies": set(),
        "config_schemas": {},
        "imports": [],
    }

    for mixin_name in composition:
        mixin = discovery.get_mixin(mixin_name)

        # Add mixin info
        code_context["mixins"].append(
            {
                "name": mixin.name,
                "version": mixin.version,
                "category": mixin.category,
            }
        )

        # Collect dependencies
        deps = discovery.get_mixin_dependencies(mixin_name)
        code_context["all_dependencies"].update(deps)

        # Collect config schemas
        if mixin.config_schema:
            code_context["config_schemas"][mixin.name] = mixin.config_schema

    print("Code generation context collected:")
    print(f"\n  Mixins to implement: {len(code_context['mixins'])}")
    for mixin_info in code_context["mixins"]:
        print(f"    • {mixin_info['name']} ({mixin_info['category']})")

    print(f"\n  Total dependencies: {len(code_context['all_dependencies'])}")
    for dep in sorted(code_context["all_dependencies"])[:5]:  # Show first 5
        print(f"    • {dep}")
    if len(code_context["all_dependencies"]) > 5:
        print(f"    ... and {len(code_context['all_dependencies']) - 5} more")

    print(f"\n  Configuration schemas: {len(code_context['config_schemas'])}")
    for mixin_name, schema in code_context["config_schemas"].items():
        print(f"    • {mixin_name}: {len(schema)} config options")

    print("\nReady for code generation!")


def main() -> None:
    """Run all examples."""
    examples = [
        example_1_list_all_mixins,
        example_2_browse_by_category,
        example_3_check_compatibility,
        example_4_dependency_resolution,
        example_5_validate_composition,
        example_6_intelligent_composition,
        example_7_mixin_details,
        example_8_code_generation_context,
    ]

    for i, example_func in enumerate(examples, 1):
        example_func()
        if i < len(examples):
            print("\n" + "=" * 80)
            print()


if __name__ == "__main__":
    main()
