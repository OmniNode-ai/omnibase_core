#!/usr/bin/env python3
"""
Quick verification script for model_node_type fixes.
This tests the specific areas that had MyPy unreachable statement issues.
"""

import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_validators():
    """Test the validators that had unreachable statement issues."""

    try:
        from omnibase_core.enums.enum_config_category import EnumConfigCategory
        from omnibase_core.enums.enum_type_name import EnumTypeName
        from omnibase_core.models.core.model_node_type import ModelNodeType

        print("✅ Import successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

    # Test type name validation (previously had unreachable issues around line 85-114)
    try:
        # Valid type name
        node1 = ModelNodeType(
            type_name="CONTRACT_TO_MODEL",
            description="Test node",
            category="generation",
        )
        assert node1.type_name == "CONTRACT_TO_MODEL"
        print("✅ Valid type_name validation works")

        # Test with enum (should convert to string)
        node2 = ModelNodeType(
            type_name=EnumTypeName.CONTRACT_TO_MODEL,
            description="Test node",
            category="generation",
        )
        assert node2.type_name == "CONTRACT_TO_MODEL"
        print("✅ Enum type_name conversion works")

    except Exception as e:
        print(f"❌ Type name validation failed: {e}")
        return False

    # Test category validation (previously had unreachable issues around line 116-145)
    try:
        # Valid category
        node3 = ModelNodeType(
            type_name="TEST_NODE", description="Test node", category="validation"
        )
        assert node3.category == "validation"
        print("✅ Valid category validation works")

        # Test with enum (should convert to string)
        node4 = ModelNodeType(
            type_name="TEST_NODE2",
            description="Test node",
            category=EnumConfigCategory.GENERATION,
        )
        assert node4.category == "generation"
        print("✅ Enum category conversion works")

    except Exception as e:
        print(f"❌ Category validation failed: {e}")
        return False

    # Test dependencies validation (previously had type issues around line 168-172)
    try:
        from uuid import uuid4

        # Test with mixed string and UUID dependencies
        test_uuid = uuid4()
        node5 = ModelNodeType(
            type_name="TEST_NODE3",
            description="Test node",
            category="test",
            dependencies=["string_dep", str(test_uuid), test_uuid],
        )
        print(
            f"✅ Dependencies validation works: {len(node5.dependencies)} dependencies"
        )

    except Exception as e:
        print(f"❌ Dependencies validation failed: {e}")
        return False

    # Test factory methods still work
    try:
        contract_node = ModelNodeType.CONTRACT_TO_MODEL()
        assert contract_node.type_name == "CONTRACT_TO_MODEL"
        assert contract_node.category == "generation"
        print("✅ Factory method works")

    except Exception as e:
        print(f"❌ Factory method failed: {e}")
        return False

    return True


def test_error_cases():
    """Test cases that should raise validation errors."""

    from omnibase_core.models.core.model_node_type import ModelNodeType

    # Test invalid type names (should raise ValueError)
    invalid_names = [
        "",  # Empty
        " ",  # Whitespace only
        "invalid name",  # Contains space
        " TRIM_ME ",  # Leading/trailing whitespace
        "node_logger_emit_log_event",  # Specific invalid name
        "scenario_runner",  # Specific invalid name
        "invalid",  # Starts with lowercase
        "123INVALID",  # Starts with digit
        "INVALID_NODE",  # Known invalid
    ]

    for invalid_name in invalid_names:
        try:
            ModelNodeType(type_name=invalid_name, description="Test", category="test")
            print(f"❌ Should have failed for type_name: '{invalid_name}'")
            return False
        except ValueError:
            pass  # Expected
        except Exception as e:
            print(f"❌ Wrong exception type for type_name '{invalid_name}': {e}")
            return False

    print("✅ Invalid type_name validation works")

    # Test invalid categories
    invalid_categories = [
        "",  # Empty
        " ",  # Whitespace only
        "Invalid Category",  # Contains space
        " trim_me ",  # Leading/trailing whitespace
        "Uppercase",  # Starts with uppercase
        "123category",  # Starts with digit
        "INVALID_CATEGORY",  # Known invalid
    ]

    for invalid_category in invalid_categories:
        try:
            ModelNodeType(
                type_name="TEST_NODE", description="Test", category=invalid_category
            )
            print(f"❌ Should have failed for category: '{invalid_category}'")
            return False
        except ValueError:
            pass  # Expected
        except Exception as e:
            print(f"❌ Wrong exception type for category '{invalid_category}': {e}")
            return False

    print("✅ Invalid category validation works")
    return True


if __name__ == "__main__":
    print("🔍 Testing model_node_type fixes...")
    print()

    success = True
    success &= test_validators()
    print()
    success &= test_error_cases()
    print()

    if success:
        print(
            "🎉 All tests passed! The MyPy unreachable statement fixes are working correctly."
        )
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)
