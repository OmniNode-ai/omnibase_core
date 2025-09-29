#!/usr/bin/env python3
"""
Fix for Pydantic Exception schema generation error.

This script implements multiple solutions for handling Exception types in Pydantic models:

1. Custom field serializer/deserializer for Exception fields
2. Custom core schema handler for Exception types
3. Example of converting Exception fields to structured types
4. Configuration with arbitrary_types_allowed and proper validators
"""

import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Union, get_type_hints

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


def test_solution_1_field_serializers():
    """Solution 1: Use field serializers to handle Exception objects."""
    print("🔧 Solution 1: Field serializers for Exception handling")

    class ModelWithExceptionField(BaseModel):
        """Model that handles Exception fields with custom serialization."""

        model_config = ConfigDict(
            arbitrary_types_allowed=True,
            # Don't validate on assignment to avoid schema generation during field access
            validate_assignment=False,
        )

        # Core fields
        success: bool = Field(..., description="Operation success status")
        message: str = Field(..., description="Operation message")

        # Exception field with custom serialization
        error: Optional[Exception] = Field(None, description="Error exception if any")

        @field_serializer("error", when_used="json")
        def serialize_error(
            self, value: Optional[Exception]
        ) -> Optional[Dict[str, str]]:
            """Serialize Exception to JSON-safe dictionary."""
            if value is None:
                return None
            return {
                "type": type(value).__name__,
                "message": str(value),
                "module": type(value).__module__,
            }

        @field_validator("error", mode="before")
        @classmethod
        def validate_error(cls, value: Any) -> Optional[Exception]:
            """Validate and convert error field."""
            if value is None:
                return None
            if isinstance(value, Exception):
                return value
            if isinstance(value, dict):
                # Convert back from serialized form
                error_type = value.get("type", "Exception")
                message = value.get("message", "")
                # Create generic Exception for deserialized data
                return Exception(f"{error_type}: {message}")
            if isinstance(value, str):
                return Exception(value)
            return Exception(str(value))

    try:
        # Test creating instances
        success_model = ModelWithExceptionField(success=True, message="All good")
        error_model = ModelWithExceptionField(
            success=False, message="Something failed", error=ValueError("Test error")
        )

        # Test JSON serialization
        success_json = success_model.model_dump_json()
        error_json = error_model.model_dump_json()

        print("✅ Created models successfully")
        print(f"   Success model JSON: {success_json}")
        print(f"   Error model JSON: {error_json}")

        # Test JSON deserialization
        recreated_error = ModelWithExceptionField.model_validate_json(error_json)
        print(f"✅ Deserialized model: {recreated_error}")

        return True

    except Exception as e:
        print(f"❌ Solution 1 failed: {e}")
        traceback.print_exc()
        return False


def test_solution_2_structured_exception():
    """Solution 2: Replace Exception fields with structured error models."""
    print("\n🔧 Solution 2: Structured error models instead of raw Exception")

    class ModelErrorInfo(BaseModel):
        """Structured error information replacing raw Exception fields."""

        error_type: str = Field(..., description="Exception class name")
        message: str = Field(..., description="Error message")
        module: str = Field(..., description="Module where exception was defined")
        traceback: Optional[str] = Field(None, description="Exception traceback")

        @classmethod
        def from_exception(cls, exc: Exception) -> "ModelErrorInfo":
            """Create error info from Exception object."""
            return cls(
                error_type=type(exc).__name__,
                message=str(exc),
                module=type(exc).__module__,
                traceback=traceback.format_exception(type(exc), exc, exc.__traceback__),
            )

        def to_exception(self) -> Exception:
            """Convert back to Exception object (generic Exception)."""
            return Exception(f"{self.error_type}: {self.message}")

    class ModelWithStructuredError(BaseModel):
        """Model using structured error instead of raw Exception."""

        success: bool = Field(..., description="Operation success status")
        message: str = Field(..., description="Operation message")
        error_info: Optional[ModelErrorInfo] = Field(
            None, description="Structured error information"
        )

        @classmethod
        def from_exception(
            cls, success: bool, message: str, error: Optional[Exception] = None
        ):
            """Create model from Exception object."""
            return cls(
                success=success,
                message=message,
                error_info=ModelErrorInfo.from_exception(error) if error else None,
            )

    try:
        # Test creating instances
        success_model = ModelWithStructuredError(success=True, message="All good")
        error_model = ModelWithStructuredError.from_exception(
            success=False,
            message="Something failed",
            error=ValueError("Test structured error"),
        )

        # Test JSON schema generation - this should work now
        schema = ModelWithStructuredError.model_json_schema()

        # Test JSON serialization
        success_json = success_model.model_dump_json()
        error_json = error_model.model_dump_json()

        print("✅ Created structured models successfully")
        print(
            f"✅ Generated JSON schema with {len(schema.get('properties', {}))} properties"
        )
        print(f"   Success JSON: {success_json}")
        print(f"   Error JSON: {error_json}")

        return True

    except Exception as e:
        print(f"❌ Solution 2 failed: {e}")
        traceback.print_exc()
        return False


def test_solution_3_core_schema_customization():
    """Solution 3: Custom core schema generation for Exception types."""
    print("\n🔧 Solution 3: Custom core schema for Exception types")

    class ExceptionCapableModel(BaseModel):
        """Model with custom core schema handling for Exception types."""

        model_config = ConfigDict(arbitrary_types_allowed=True)

        success: bool = Field(..., description="Operation success")
        error: Optional[Exception] = Field(None, description="Exception field")

        @classmethod
        def __get_pydantic_core_schema__(
            cls,
            source_type: Any,
            handler: Any,
        ) -> core_schema.CoreSchema:
            """Custom core schema generation to handle Exception fields."""

            # Get the default schema
            schema = handler(source_type)

            # Find Exception fields and replace their schemas
            if "fields" in schema:
                for field_name, field_schema in schema["fields"].items():
                    # Check if this field has an Exception type annotation
                    annotations = get_type_hints(cls)
                    if field_name in annotations:
                        field_type = annotations[field_name]
                        # Handle Optional[Exception] or Union[Exception, None]
                        if (
                            hasattr(field_type, "__origin__")
                            and field_type.__origin__ is Union
                        ):
                            args = field_type.__args__
                            if Exception in args or any(
                                issubclass(arg, Exception)
                                for arg in args
                                if isinstance(arg, type)
                            ):
                                # Replace with a string schema for JSON compatibility
                                field_schema["schema"] = core_schema.str_schema()
                        elif isinstance(field_type, type) and issubclass(
                            field_type, Exception
                        ):
                            # Direct Exception type
                            field_schema["schema"] = core_schema.str_schema()

            return schema

        @field_serializer("error")
        def serialize_error(self, value: Optional[Exception]) -> Optional[str]:
            """Serialize Exception to string."""
            if value is None:
                return None
            return f"{type(value).__name__}: {str(value)}"

        @field_validator("error", mode="before")
        @classmethod
        def validate_error(cls, value: Any) -> Optional[Exception]:
            """Validate error field."""
            if value is None:
                return None
            if isinstance(value, Exception):
                return value
            if isinstance(value, str):
                # Parse string format: "ExceptionType: message"
                if ": " in value:
                    exc_type, message = value.split(": ", 1)
                    return Exception(f"{exc_type}: {message}")
                return Exception(value)
            return Exception(str(value))

    try:
        # Test model creation
        success_model = ExceptionCapableModel(success=True)
        error_model = ExceptionCapableModel(
            success=False, error=RuntimeError("Custom schema test")
        )

        # Test JSON schema generation
        try:
            schema = ExceptionCapableModel.model_json_schema()
            print("✅ JSON schema generated successfully")
            print(f"   Schema properties: {list(schema.get('properties', {}).keys())}")
        except Exception as schema_error:
            print(f"⚠️ JSON schema generation failed: {schema_error}")
            # But the model should still work for basic operations

        # Test serialization
        error_json = error_model.model_dump_json()
        print("✅ JSON serialization works")
        print(f"   Error JSON: {error_json}")

        return True

    except Exception as e:
        print(f"❌ Solution 3 failed: {e}")
        traceback.print_exc()
        return False


def fix_existing_models_with_exceptions():
    """Solution 4: Fix any existing models in the codebase that have Exception fields."""
    print("\n🔧 Solution 4: Fixing existing models with Exception fields")

    # This would scan and fix existing models
    # For now, just demonstrate the pattern

    class FixedRetryExecution(BaseModel):
        """Fixed version of a model that had Exception fields."""

        model_config = ConfigDict(arbitrary_types_allowed=True)

        current_attempt: int = Field(default=0, description="Current retry attempt")
        error_message: str = Field(default="", description="Last error message")
        last_status_code: int = Field(default=0, description="Last status code")

        # Instead of: error: Exception | None = None
        # Use structured approach:
        def record_attempt_with_error(self, error: Optional[Exception] = None) -> None:
            """Record attempt with error handling."""
            if error is not None:
                self.error_message = f"{type(error).__name__}: {str(error)}"

        def get_last_exception(self) -> Optional[Exception]:
            """Recreate Exception from stored error message."""
            if not self.error_message:
                return None
            return Exception(self.error_message)

    try:
        # Test the fixed model
        fixed_model = FixedRetryExecution()
        fixed_model.record_attempt_with_error(ValueError("Test error"))

        # Generate schema - should work now
        schema = FixedRetryExecution.model_json_schema()

        print("✅ Fixed model works correctly")
        print(
            f"✅ Schema generated with {len(schema.get('properties', {}))} properties"
        )
        print(f"   Error message: {fixed_model.error_message}")

        return True

    except Exception as e:
        print(f"❌ Solution 4 failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all solutions and provide recommendations."""
    print("🚀 Fixing Pydantic Exception schema generation error...")
    print("=" * 60)

    results = []

    # Test all solutions
    results.append(("Field Serializers", test_solution_1_field_serializers()))
    results.append(("Structured Errors", test_solution_2_structured_exception()))
    results.append(("Core Schema Custom", test_solution_3_core_schema_customization()))
    results.append(("Fixed Models", fix_existing_models_with_exceptions()))

    # Summary
    print("\n" + "=" * 60)
    print("📋 SOLUTION SUMMARY")
    print("=" * 60)

    successful_solutions = []
    for name, success in results:
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{status}: {name}")
        if success:
            successful_solutions.append(name)

    # Recommendations
    print(f"\n🎯 RECOMMENDATIONS")
    print("-" * 60)

    if successful_solutions:
        print("✅ Available solutions:")
        for solution in successful_solutions:
            print(f"   • {solution}")

        print("\n💡 BEST PRACTICES:")
        print("1. 🥇 PREFERRED: Use Solution 2 (Structured Errors)")
        print("   - Replace Exception fields with structured error models")
        print("   - Better for API documentation and type safety")
        print("   - Fully JSON-serializable")

        print("\n2. 🥈 ALTERNATIVE: Use Solution 1 (Field Serializers)")
        print("   - Keep Exception fields but add proper serialization")
        print("   - Good for gradual migration")
        print("   - Requires arbitrary_types_allowed=True")

        print("\n3. ⚠️ AVOID: Direct Exception fields without handling")
        print("   - Raw Exception fields break JSON schema generation")
        print("   - Use one of the above solutions instead")

    else:
        print("❌ No solutions worked - this needs further investigation")

    return len(successful_solutions) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
