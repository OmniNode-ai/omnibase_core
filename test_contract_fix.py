#!/usr/bin/env python3
"""
Test script to verify our ModelContractBase fixes work correctly.
This tests the critical changes without requiring the full dependency chain.
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test the critical imports we fixed
try:
    from omnibase_core.core.contracts.model_dependency import ModelDependency
    from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
    from omnibase_core.enums import EnumNodeType
    from omnibase_core.models.core.model_semver import ModelSemVer

    print("✅ Core imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test ModelContractBase fixes without importing the full class
print("\n🧪 Testing dependency validation fixes...")

# Test 1: ModelDependency can be created from dict (YAML compatibility)
try:
    test_dict = {
        "name": "TestProtocol",
        "module": "omnibase_core.test.protocol",
        "dependency_type": "protocol",
        "required": True,
    }

    # This should work now
    dependency = ModelDependency(**test_dict)
    print(f"✅ Dict to ModelDependency conversion: {dependency.name}")
except Exception as e:
    print(f"❌ Dict conversion failed: {e}")

# Test 2: EnumNodeType can be created from string (YAML compatibility)
try:
    from omnibase_core.enums.enum_node_type import EnumNodeType

    # Test string to enum conversion
    node_type_str = "COMPUTE"
    node_type_enum = EnumNodeType(node_type_str)
    print(f"✅ String to EnumNodeType conversion: {node_type_enum}")
except Exception as e:
    print(f"❌ String to enum conversion failed: {e}")

# Test 3: Validate our specific validation logic
print("\n🔍 Testing validation logic...")


# Create a minimal validator to test our fixes
class TestValidator:
    @classmethod
    def validate_dependencies_structured_only(cls, v):
        """Test our fixed dependency validation logic"""
        if not v:
            return []

        if not isinstance(v, list):
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_FAILED,
                message=f"Contract dependencies must be a list, got {type(v)}",
                context={"input_type": str(type(v))},
            )

        dependencies = []
        for i, item in enumerate(v):
            if isinstance(item, ModelDependency):
                dependencies.append(item)
            elif isinstance(item, dict):
                # This is our fix - convert dict from YAML to ModelDependency instance
                try:
                    dependencies.append(ModelDependency(**item))
                except Exception as e:
                    raise OnexError(
                        error_code=CoreErrorCode.VALIDATION_FAILED,
                        message=f"Failed to convert dependency dict {i} to ModelDependency: {str(e)}",
                        context={
                            "dependency_index": i,
                            "dict_keys": (
                                list(item.keys()) if isinstance(item, dict) else None
                            ),
                            "original_error": str(e),
                        },
                    ) from e
            else:
                # Reject all other types
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                    message=f"Dependency {i} must be ModelDependency instance or dict. Received {type(item).__name__}.",
                    context={
                        "dependency_index": i,
                        "received_type": str(type(item)),
                        "expected_types": ["ModelDependency", "dict"],
                        "onex_principle": "Strong types with YAML dict conversion support",
                    },
                )

        return dependencies

    @classmethod
    def validate_node_type_enum_only(cls, v):
        """Test our fixed node_type validation logic"""
        if isinstance(v, EnumNodeType):
            return v
        elif isinstance(v, str):
            # Convert string from YAML to EnumNodeType instance
            try:
                return EnumNodeType(v)
            except ValueError:
                msg = f"node_type string '{v}' is not a valid EnumNodeType value. Valid values: {list(EnumNodeType)}"
                raise ValueError(msg)
        else:
            msg = f"node_type must be EnumNodeType enum instance or valid enum value string, not {type(v).__name__}."
            raise ValueError(msg)


# Test the validation logic
test_cases = [
    # Test dict conversion (the main fix)
    {
        "name": "dict_conversion",
        "input": [
            {"name": "TestDep", "module": "test.module", "dependency_type": "protocol"}
        ],
        "should_pass": True,
    },
    # Test ModelDependency instance (should still work)
    {
        "name": "model_dependency_instance",
        "input": [ModelDependency(name="TestDep2", dependency_type="protocol")],
        "should_pass": True,
    },
    # Test invalid type (should fail)
    {
        "name": "invalid_string",
        "input": ["invalid_string_dependency"],
        "should_pass": False,
    },
]

validator = TestValidator()

for test_case in test_cases:
    try:
        result = validator.validate_dependencies_structured_only(test_case["input"])
        if test_case["should_pass"]:
            print(
                f"✅ {test_case['name']}: Passed as expected - {len(result)} dependencies"
            )
        else:
            print(f"❌ {test_case['name']}: Should have failed but passed")
    except Exception as e:
        if not test_case["should_pass"]:
            print(f"✅ {test_case['name']}: Failed as expected - {e}")
        else:
            print(f"❌ {test_case['name']}: Should have passed but failed - {e}")

# Test node type validation
print("\n🔍 Testing node type validation...")

node_type_test_cases = [
    {"name": "enum_instance", "input": EnumNodeType.COMPUTE, "should_pass": True},
    {"name": "valid_string", "input": "COMPUTE", "should_pass": True},
    {"name": "invalid_string", "input": "INVALID_TYPE", "should_pass": False},
    {"name": "invalid_type", "input": 123, "should_pass": False},
]

for test_case in node_type_test_cases:
    try:
        result = validator.validate_node_type_enum_only(test_case["input"])
        if test_case["should_pass"]:
            print(f"✅ {test_case['name']}: Passed as expected - {result}")
        else:
            print(f"❌ {test_case['name']}: Should have failed but passed")
    except Exception as e:
        if not test_case["should_pass"]:
            print(f"✅ {test_case['name']}: Failed as expected - {e}")
        else:
            print(f"❌ {test_case['name']}: Should have passed but failed - {e}")

print("\n🎉 Contract validation fix testing completed!")
