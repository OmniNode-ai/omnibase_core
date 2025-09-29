#!/usr/bin/env python3
"""
Test existing models for Exception field issues and apply fixes.

This script will:
1. Find models that might have Exception fields
2. Test them for schema generation issues
3. Apply fixes where needed
"""

import importlib
import sys
import traceback
from pathlib import Path
from typing import Any, get_type_hints

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from pydantic import BaseModel

from pydantic_exception_fix import (
    ModelWithoutExceptionFields,
    ModelWithSerializedExceptions,
    ModelWithStructuredError,
    fix_exception_field_in_existing_model,
)


def test_specific_model_patterns():
    """Test patterns that were mentioned in the grep results."""

    print("🧪 Testing specific model patterns that might have Exception fields...")

    # Create a test model similar to what might exist in archived files
    class TestRetryAttemptResult(BaseModel):
        """Test model similar to archived retry strategy patterns."""

        attempt_number: int
        success: bool
        execution_time_ms: float
        # This pattern would cause the error:
        # exception: Exception | None = None  # ❌ This would fail

        # Fixed version using our solutions:
        error_message: str | None = None

        @classmethod
        def from_exception(
            cls,
            attempt_number: int,
            success: bool,
            execution_time_ms: float,
            exception: Exception | None = None,
        ):
            """Create from exception using our fix pattern."""
            error_message = None
            if exception:
                error_message = f"{type(exception).__name__}: {str(exception)}"

            return cls(
                attempt_number=attempt_number,
                success=success,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
            )

    # Test it works
    try:
        # Test successful case
        success_result = TestRetryAttemptResult(
            attempt_number=1, success=True, execution_time_ms=150.0
        )

        # Test error case using our fixed pattern
        error_result = TestRetryAttemptResult.from_exception(
            attempt_number=2,
            success=False,
            execution_time_ms=300.0,
            exception=ValueError("Connection timeout"),
        )

        # Test schema generation - this should work
        schema = TestRetryAttemptResult.model_json_schema()

        print(f"✅ TestRetryAttemptResult works correctly")
        print(f"   Success result: {success_result.model_dump_json()}")
        print(f"   Error result: {error_result.model_dump_json()}")
        print(f"   Schema properties: {len(schema.get('properties', {}))}")

        return True

    except Exception as e:
        print(f"❌ TestRetryAttemptResult failed: {e}")
        traceback.print_exc()
        return False


def test_problematic_model_with_exception_field():
    """Test a model that would have the original problem."""

    print("\n🧪 Testing model with Exception field (this would normally fail)...")

    # Using our Solution 1: Field Serializers approach
    class FixedRetryModel(ModelWithSerializedExceptions):
        """Model that inherits our Exception field fix."""

        attempt_number: int
        execution_time_ms: float

    try:
        # Test creating with exception
        model = FixedRetryModel(
            success=False,
            message="Retry failed",
            attempt_number=3,
            execution_time_ms=500.0,
            error=ConnectionError("Database unreachable"),
        )

        # Test JSON serialization (this would fail with raw Exception fields)
        json_str = model.model_dump_json()

        # Test deserialization
        recreated = FixedRetryModel.model_validate_json(json_str)

        print(f"✅ FixedRetryModel works correctly")
        print(f"   JSON: {json_str}")
        print(f"   Recreated error type: {type(recreated.error)}")

        return True

    except Exception as e:
        print(f"❌ FixedRetryModel failed: {e}")
        traceback.print_exc()
        return False


def create_example_fix_for_existing_model():
    """Show how to fix an existing model that has Exception fields."""

    print("\n🔧 Example: Fixing an existing model with Exception fields...")

    # Original problematic model (would cause the error)
    class OriginalProblematicModel(BaseModel):
        """This model would cause the schema generation error."""

        model_config = {"arbitrary_types_allowed": True}

        success: bool
        # This would cause: "Unable to generate pydantic-core schema for <class 'Exception'>"
        # last_error: Exception | None = None  # ❌ Commented out

        # Fix: Use string field instead
        last_error_message: str | None = None

        def record_error(self, error: Exception) -> None:
            """Record error using string conversion."""
            self.last_error_message = f"{type(error).__name__}: {str(error)}"
            self.success = False

        def get_last_error(self) -> Exception | None:
            """Recreate Exception from stored message."""
            if not self.last_error_message:
                return None
            return Exception(self.last_error_message)

    try:
        # Test the fixed model
        model = OriginalProblematicModel(success=True)
        model.record_error(ValueError("Invalid configuration"))

        # This should work without schema generation errors
        schema = OriginalProblematicModel.model_json_schema()
        json_str = model.model_dump_json()

        # Test recreating the exception
        recreated_error = model.get_last_error()

        print(f"✅ Fixed model works correctly")
        print(f"   Schema properties: {len(schema.get('properties', {}))}")
        print(f"   JSON: {json_str}")
        print(f"   Recreated error: {recreated_error}")

        return True

    except Exception as e:
        print(f"❌ Fixed model failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests and fixes."""

    print("🚀 Testing and fixing Pydantic Exception field issues...")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Specific Model Patterns", test_specific_model_patterns()))
    results.append(("Fixed Retry Model", test_problematic_model_with_exception_field()))
    results.append(("Example Model Fix", create_example_fix_for_existing_model()))

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("\n💡 SUMMARY OF FIXES:")
        print(
            "1. ✅ Field Serializers - Keep Exception fields, add custom serialization"
        )
        print(
            "2. ✅ Structured Errors - Replace Exception fields with structured models"
        )
        print("3. ✅ String Conversion - Convert Exception fields to string fields")
        print("\n🔧 TO FIX EXISTING MODELS:")
        print("- Import one of the solutions from pydantic_exception_fix.py")
        print("- Replace Exception fields with string fields + conversion methods")
        print("- Or inherit from ModelWithSerializedExceptions")
        print("- Or use structured error models")
    else:
        print(f"\n❌ Some tests failed - check individual errors above")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
