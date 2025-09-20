#!/usr/bin/env python3
"""
Comprehensive verification test script for strong typing improvements.
"""

import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Tuple


def test_basic_imports() -> Tuple[bool, List[str]]:
    """Test basic imports of all models and enums."""
    errors = []
    success = True

    # Test enum imports
    try:
        import omnibase_core.enums as enums
        # Test specific enum imports
        from omnibase_core.enums import EnumTrendType, EnumTimePeriod, EnumSchemaValueType
        print("✓ Successfully imported enums")
    except Exception as e:
        errors.append(f"Enum import failed: {e}")
        success = False
        traceback.print_exc()

    # Test core model imports
    try:
        import omnibase_core.models.core as core_models
        print("✓ Successfully imported core models module")
    except Exception as e:
        errors.append(f"Core model module import failed: {e}")
        success = False
        traceback.print_exc()

    # Test specific critical imports
    try:
        from omnibase_core.models.core import ModelExample, ModelSchemaValue, ModelSchemaValueFactory
        print("✓ Successfully imported critical models")
    except Exception as e:
        errors.append(f"Critical model import failed: {e}")
        success = False
        traceback.print_exc()

    return success, errors


def test_uuid_generation() -> Tuple[bool, List[str]]:
    """Test UUID generation in models."""
    errors = []
    success = True

    try:
        from omnibase_core.models.core import ModelExample

        # Test UUID generation
        example1 = ModelExample()
        example2 = ModelExample()

        # Check if UUIDs are generated
        if example1.example_id is None:
            errors.append("ModelExample UUID not generated automatically")
            success = False

        if example2.example_id is None:
            errors.append("ModelExample UUID not generated automatically (second instance)")
            success = False

        # Check if UUIDs are unique
        if example1.example_id == example2.example_id:
            errors.append("ModelExample UUIDs are not unique")
            success = False

        if success:
            print(f"✓ UUID generation working: {example1.example_id}, {example2.example_id}")

    except Exception as e:
        errors.append(f"UUID generation test failed: {e}")
        success = False
        traceback.print_exc()

    return success, errors


def test_enum_usage() -> Tuple[bool, List[str]]:
    """Test enum usage in models."""
    errors = []
    success = True

    try:
        from omnibase_core.models.core import ModelTrendData
        from omnibase_core.enums import EnumTrendType, EnumTimePeriod

        # Test enum usage
        trend = ModelTrendData(
            trend_name="test_trend",
            trend_type=EnumTrendType.LINEAR,
            time_period=EnumTimePeriod.DAY
        )

        if trend.trend_type != EnumTrendType.LINEAR:
            errors.append("Enum assignment failed in ModelTrendData")
            success = False

        if success:
            print(f"✓ Enum usage working: {trend.trend_type}, {trend.time_period}")

    except Exception as e:
        errors.append(f"Enum usage test failed: {e}")
        success = False
        traceback.print_exc()

    return success, errors


def test_factory_patterns() -> Tuple[bool, List[str]]:
    """Test factory patterns."""
    errors = []
    success = True

    try:
        from omnibase_core.models.core import ModelSchemaValueFactory

        # Test factory method
        schema_val = ModelSchemaValueFactory.from_value("test")

        if schema_val.value_type != "string":
            errors.append(f"Factory pattern failed: expected 'string', got '{schema_val.value_type}'")
            success = False

        if success:
            print(f"✓ Factory pattern working: {schema_val.value_type}")

    except Exception as e:
        errors.append(f"Factory pattern test failed: {e}")
        success = False
        traceback.print_exc()

    return success, errors


def test_serialization() -> Tuple[bool, List[str]]:
    """Test serialization and deserialization."""
    errors = []
    success = True

    try:
        from omnibase_core.models.core import ModelExample

        # Create instance
        example = ModelExample()

        # Test serialization
        data = example.model_dump()
        if not isinstance(data, dict):
            errors.append("Serialization failed: model_dump() did not return dict")
            success = False

        # Test deserialization
        example2 = ModelExample.model_validate(data)
        if example2.example_id != example.example_id:
            errors.append("Deserialization failed: UUIDs don't match")
            success = False

        if success:
            print("✓ Serialization/deserialization working")

    except Exception as e:
        errors.append(f"Serialization test failed: {e}")
        success = False
        traceback.print_exc()

    return success, errors


def test_trend_point_validation() -> Tuple[bool, List[str]]:
    """Test field validation using ModelTrendPoint."""
    errors = []
    success = True

    try:
        from omnibase_core.models.core import ModelTrendPoint

        # Test valid creation
        point = ModelTrendPoint(timestamp=datetime.now(), value=100.0)

        # Test validation method if it exists
        if hasattr(point, 'is_reliable'):
            reliable = point.is_reliable()
            print(f"✓ Validation method working: is_reliable() = {reliable}")
        else:
            print("✓ ModelTrendPoint created successfully (no is_reliable method)")

    except Exception as e:
        errors.append(f"Validation test failed: {e}")
        success = False
        traceback.print_exc()

    return success, errors


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("COMPREHENSIVE STRONG TYPING VERIFICATION")
    print("=" * 60)

    test_results = []

    # Run all tests
    tests = [
        ("Basic Imports", test_basic_imports),
        ("UUID Generation", test_uuid_generation),
        ("Enum Usage", test_enum_usage),
        ("Factory Patterns", test_factory_patterns),
        ("Serialization", test_serialization),
        ("Validation", test_trend_point_validation),
    ]

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        success, errors = test_func()
        test_results.append((test_name, success, errors))

        if not success:
            print(f"✗ {test_name} FAILED")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"✓ {test_name} PASSED")

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, success, _ in test_results if success)
    total = len(test_results)

    for test_name, success, errors in test_results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:20} : {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())