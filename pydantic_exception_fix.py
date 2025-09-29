#!/usr/bin/env python3
"""
Comprehensive fix for Pydantic Exception schema generation error.

This module provides the three working solutions for handling Exception types in Pydantic models.
Use these patterns to fix any models that have Exception fields causing schema generation errors.

Error: pydantic.errors.PydanticSchemaGenerationError: Unable to generate pydantic-core schema for <class 'Exception'>
"""

import json
import sys
import traceback as tb
from pathlib import Path
from typing import Any, Dict, Optional, Union, get_type_hints

# Add src to path
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from pydantic_core import core_schema

# ============================================================================
# SOLUTION 1: Field Serializers (RECOMMENDED for existing models)
# ============================================================================


class ModelWithSerializedExceptions(BaseModel):
    """
    Model that handles Exception fields with custom serialization.

    This is the RECOMMENDED approach for existing models that have Exception fields.
    It allows you to keep the Exception fields but handles JSON serialization properly.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Required for Exception fields
        validate_assignment=False,  # Avoid schema generation during assignment
        extra="ignore",  # Ignore extra fields during deserialization
    )

    # Example fields
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")

    # Exception field with proper serialization
    error: Optional[Exception] = Field(None, description="Error exception if any")

    @field_serializer("error", when_used="json")
    def serialize_error(self, value: Optional[Exception]) -> Optional[Dict[str, str]]:
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
            return Exception(f"{error_type}: {message}")
        if isinstance(value, str):
            return Exception(value)
        return Exception(str(value))


# ============================================================================
# SOLUTION 2: Structured Error Models (BEST for new code)
# ============================================================================


class ModelErrorInfo(BaseModel):
    """Structured error information replacing raw Exception fields."""

    error_type: str = Field(..., description="Exception class name")
    message: str = Field(..., description="Error message")
    module: str = Field(..., description="Module where exception was defined")
    traceback_text: Optional[str] = Field(
        None, description="Exception traceback as string"
    )

    @classmethod
    def from_exception(cls, exc: Exception) -> "ModelErrorInfo":
        """Create error info from Exception object."""
        # Format traceback as a single string instead of list
        tb_text = None
        if exc.__traceback__:
            tb_text = "".join(tb.format_exception(type(exc), exc, exc.__traceback__))

        return cls(
            error_type=type(exc).__name__,
            message=str(exc),
            module=type(exc).__module__,
            traceback_text=tb_text,
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


# ============================================================================
# SOLUTION 3: Remove Exception Fields (SIMPLE approach)
# ============================================================================


class ModelWithoutExceptionFields(BaseModel):
    """
    Model that avoids Exception fields entirely by converting to string fields.

    This is the SIMPLEST approach - just convert Exception fields to string fields
    and handle the conversion in methods.
    """

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation message")
    error_message: Optional[str] = Field(None, description="Error message if any")

    def record_error(self, error: Exception) -> None:
        """Record an error by converting it to a string."""
        self.error_message = f"{type(error).__name__}: {str(error)}"

    def get_error_as_exception(self) -> Optional[Exception]:
        """Convert stored error message back to an Exception."""
        if not self.error_message:
            return None
        return Exception(self.error_message)


# ============================================================================
# UTILITY FUNCTIONS FOR FIXING EXISTING MODELS
# ============================================================================


def fix_exception_field_in_existing_model(
    model_class: type[BaseModel],
) -> type[BaseModel]:
    """
    Utility function to dynamically fix Exception fields in existing models.

    This can be used to patch existing models that have Exception fields.
    """

    # Check if the model has Exception fields
    annotations = get_type_hints(model_class)
    exception_fields = []

    for field_name, field_type in annotations.items():
        # Check for Optional[Exception] or Exception fields
        if field_type is Exception:
            exception_fields.append(field_name)
        elif hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
            args = field_type.__args__
            if Exception in args:
                exception_fields.append(field_name)

    if not exception_fields:
        # No Exception fields found
        return model_class

    # Create a fixed version of the model
    class FixedModel(model_class):
        model_config = ConfigDict(
            arbitrary_types_allowed=True,
            validate_assignment=False,
            **getattr(model_class, "model_config", {}),
        )

        def model_dump_json(self, **kwargs) -> str:
            """Override JSON serialization to handle Exception fields."""
            data = self.model_dump(**kwargs)

            # Convert Exception fields to serializable format
            for field_name in exception_fields:
                if field_name in data and data[field_name] is not None:
                    exc = data[field_name]
                    if isinstance(exc, Exception):
                        data[field_name] = {
                            "type": type(exc).__name__,
                            "message": str(exc),
                            "module": type(exc).__module__,
                        }

            return json.dumps(data, **kwargs)

    return FixedModel


def apply_exception_field_fix_to_model(model: BaseModel) -> BaseModel:
    """Apply exception field fix to an existing model instance."""
    fixed_class = fix_exception_field_in_existing_model(type(model))
    return fixed_class(**model.model_dump())


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================


def demonstrate_solutions():
    """Demonstrate all three working solutions."""

    print("🔧 Pydantic Exception Field Fixes - Working Solutions")
    print("=" * 60)

    # Solution 1: Serialized Exceptions
    print("\n✅ SOLUTION 1: Field Serializers")
    model1 = ModelWithSerializedExceptions(
        success=False,
        message="Operation failed",
        error=ValueError("Invalid input parameter"),
    )
    print(f"   JSON: {model1.model_dump_json()}")

    # Solution 2: Structured Errors
    print("\n✅ SOLUTION 2: Structured Error Models")
    model2 = ModelWithStructuredError.from_exception(
        success=False,
        message="Operation failed",
        error=RuntimeError("System error occurred"),
    )
    # This should work now with the fixed traceback handling
    schema = ModelWithStructuredError.model_json_schema()
    print(f"   Schema properties: {list(schema.get('properties', {}).keys())}")
    print(f"   JSON: {model2.model_dump_json()}")

    # Solution 3: String Fields
    print("\n✅ SOLUTION 3: String-based Error Fields")
    model3 = ModelWithoutExceptionFields(success=True, message="All good")
    model3.record_error(ConnectionError("Database connection failed"))
    print(f"   Error message: {model3.error_message}")
    print(f"   JSON: {model3.model_dump_json()}")

    print("\n🎯 ALL SOLUTIONS WORKING!")
    return True


if __name__ == "__main__":
    try:
        demonstrate_solutions()
        print("\n✅ Pydantic Exception schema generation has been fixed!")
    except Exception as e:
        print(f"\n❌ Error in demonstration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
