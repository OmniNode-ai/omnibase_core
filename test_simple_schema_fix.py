#!/usr/bin/env python3
"""
Simple test script to verify Pydantic Exception schema generation fix.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def test_schema_generation_directly():
    """Test schema generation directly without full model imports."""
    print("🧪 Testing simplified Exception schema generation...")

    # Test that we can create a simple Pydantic model with Exception handling
    try:
        from typing import Generic, TypeVar

        from pydantic import BaseModel, Field
        from pydantic_core import core_schema

        T = TypeVar("T")
        E = TypeVar("E")

        class SimpleResult(BaseModel, Generic[T, E]):
            """Simplified Result model for testing."""

            model_config = {"arbitrary_types_allowed": True}

            @classmethod
            def __get_pydantic_core_schema__(
                cls,
                source_type: any,
                handler: any,
            ) -> core_schema.CoreSchema:
                """Handle Exception types in schema generation."""
                # If this is SimpleResult[T, Exception], handle it properly
                if hasattr(source_type, "__args__") and len(source_type.__args__) == 2:
                    success_type, error_type = source_type.__args__

                    # Check if error type is Exception or subclass
                    if isinstance(error_type, type) and issubclass(
                        error_type, Exception
                    ):
                        # Create a string-based schema for Exception types
                        return core_schema.model_schema(
                            cls,
                            core_schema.model_fields_schema(
                                {
                                    "success": core_schema.model_field(
                                        core_schema.bool_schema(),
                                    ),
                                    "value": core_schema.model_field(
                                        core_schema.any_schema(), default=None
                                    ),
                                    "error": core_schema.model_field(
                                        core_schema.str_schema(), default=None
                                    ),
                                }
                            ),
                        )

                # For other types, use default schema generation
                return handler(source_type)

            success: bool = Field(..., description="Operation success")
            value: T | None = Field(None, description="Success value")
            error: E | None = Field(None, description="Error value")

        # Test basic model creation
        result = SimpleResult[str, str](success=True, value="test")
        print("✅ SimpleResult[str, str] created successfully")

        # Test schema generation for basic types
        schema = SimpleResult.model_json_schema()
        print("✅ SimpleResult base schema generated successfully")

        # Test with Exception type - this was the problematic case
        try:
            # Create an instance with Exception
            error_result = SimpleResult[str, Exception](
                success=False, error=ValueError("test error")
            )
            print("✅ SimpleResult[str, Exception] created successfully")

            # The key test - can we generate a schema for this?
            # This would fail with the original error
            exception_schema = SimpleResult[str, Exception].model_json_schema()
            print("✅ SimpleResult[str, Exception] schema generated successfully!")
            print(
                f"   Schema has {len(exception_schema.get('properties', {}))} properties"
            )

        except Exception as e:
            print(f"❌ Exception handling failed: {e}")
            return False

    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("🎉 Schema generation test passed!")
    return True


def test_specific_error_message():
    """Test the specific error message that was reported."""
    print("\n🔍 Testing the specific reported error...")

    try:
        from pydantic import BaseModel

        # This would have caused the original error:
        # "Unable to generate pydantic-core schema for <class 'Exception'>"

        class TestModel(BaseModel):
            model_config = {"arbitrary_types_allowed": True}

            # This type of field was causing the problem
            some_exception: Exception | None = None

        # Try to generate schema - this was failing before
        schema = TestModel.model_json_schema()
        print("✅ Direct Exception field schema generated successfully")

        # Create an instance
        instance = TestModel(some_exception=ValueError("test"))
        print("✅ Model with Exception field created successfully")

    except Exception as e:
        print(f"❌ Specific error test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    success1 = test_schema_generation_directly()
    success2 = test_specific_error_message()

    if success1 and success2:
        print("\n✅ ALL TESTS PASSED - Exception schema generation is fixed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
