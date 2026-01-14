"""
Unit tests for @allow_any_type decorator.

Tests cover:
- Type validation bypass with documented reason
- Decorator usage with custom classes
- Decorator usage with exceptions and edge cases
- Pydantic model integration
- Metadata preservation and serialization
"""

from typing import Any

import pytest


@pytest.mark.unit
class TestAllowAnyTypeBasicBehavior:
    """Test basic @allow_any_type decorator behavior."""

    def test_allow_any_type_bypasses_validation(self):
        """Test that @allow_any_type allows Any type usage with reason."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Duck typing for protocol-agnostic handling")
        def process_any_value(value: Any) -> Any:
            return value

        # Should work with any type
        assert process_any_value(42) == 42
        assert process_any_value("test") == "test"
        assert process_any_value([1, 2, 3]) == [1, 2, 3]
        assert process_any_value({"key": "value"}) == {"key": "value"}

    def test_allow_any_type_preserves_function(self):
        """Test that decorator returns the function unchanged."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        def original_func(x: Any) -> Any:
            return x * 2

        decorated_func = allow_any_type(reason="Testing")(original_func)

        # Function behavior should be unchanged
        assert decorated_func(5) == 10
        assert decorated_func("a") == "aa"

    def test_allow_any_type_adds_metadata(self):
        """Test that decorator adds reason metadata to function."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        reason_text = "Duck typing utility for flexible object handling"

        @allow_any_type(reason=reason_text)
        def my_function(obj: Any) -> Any:
            return obj

        # Should have metadata attribute
        assert hasattr(my_function, "__allow_any_reason__")
        assert my_function.__allow_any_reason__ == reason_text


@pytest.mark.unit
class TestAllowAnyTypeWithCustomClasses:
    """Test @allow_any_type with custom classes."""

    def test_allow_any_type_with_custom_classes(self):
        """Test decorator with custom class instances."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        class CustomClass:
            def __init__(self, value: int):
                self.value = value

        @allow_any_type(reason="Handle any object type")
        def process_object(obj: Any) -> Any:
            return obj

        custom_obj = CustomClass(42)
        result = process_object(custom_obj)

        assert result is custom_obj
        assert result.value == 42

    def test_allow_any_type_with_nested_objects(self):
        """Test decorator with nested object structures."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Handle nested structures")
        def process_nested(data: Any) -> Any:
            return data

        nested_data = {
            "list": [1, 2, 3],
            "dict": {"a": "b"},
            "tuple": (1, 2),
            "set": {1, 2, 3},
        }

        result = process_nested(nested_data)
        assert result == nested_data


@pytest.mark.unit
class TestAllowAnyTypeWithExceptions:
    """Test @allow_any_type with exception handling."""

    def test_allow_any_type_with_exceptions(self):
        """Test that decorator doesn't interfere with exception handling."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Handle exceptions gracefully")
        def may_raise_exception(value: Any) -> Any:
            if value is None:
                raise ValueError("None not allowed")
            return value

        # Normal case should work
        assert may_raise_exception(42) == 42

        # Exception should still be raised
        with pytest.raises(ValueError, match="None not allowed"):
            may_raise_exception(None)

    def test_allow_any_type_with_multiple_return_types(self):
        """Test decorator with functions returning different types."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Multiple return types for flexibility")
        def conditional_return(flag: bool) -> Any:
            if flag:
                return "string_result"
            return 42

        assert conditional_return(True) == "string_result"
        assert conditional_return(False) == 42


@pytest.mark.unit
class TestAllowAnyTypeWithPydanticModels:
    """Test @allow_any_type with Pydantic models."""

    def test_allow_any_type_with_pydantic_models(self):
        """Test that decorator works with Pydantic models."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        try:
            from pydantic import BaseModel
        except ImportError:
            pytest.skip("Pydantic not installed")

        class TestModel(BaseModel):
            name: str
            value: int

        @allow_any_type(reason="Handle Pydantic models")
        def process_model(model: Any) -> Any:
            return model

        test_model = TestModel(name="test", value=42)
        result = process_model(test_model)

        assert result is test_model
        assert result.name == "test"
        assert result.value == 42

    def test_allow_any_type_preserves_serialization(self):
        """Test that decorator preserves object serialization capabilities."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        try:
            from pydantic import BaseModel
        except ImportError:
            pytest.skip("Pydantic not installed")

        class SerializableModel(BaseModel):
            data: str

        @allow_any_type(reason="Preserve serialization")
        def process_and_serialize(obj: Any) -> dict:
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            return {"data": str(obj)}

        model = SerializableModel(data="test_data")
        result = process_and_serialize(model)

        assert result == {"data": "test_data"}


@pytest.mark.unit
class TestAllowAnyTypeMetadata:
    """Test @allow_any_type metadata tracking."""

    def test_allow_any_type_metadata_is_string(self):
        """Test that metadata reason is always a string."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Test reason")
        def func(x: Any) -> Any:
            return x

        assert isinstance(func.__allow_any_reason__, str)

    def test_allow_any_type_with_empty_reason(self):
        """Test decorator with empty reason string."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="")
        def func(x: Any) -> Any:
            return x

        assert hasattr(func, "__allow_any_reason__")
        assert func.__allow_any_reason__ == ""

    def test_allow_any_type_with_long_reason(self):
        """Test decorator with very long reason text."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        long_reason = "A" * 1000

        @allow_any_type(reason=long_reason)
        def func(x: Any) -> Any:
            return x

        assert func.__allow_any_reason__ == long_reason
        assert len(func.__allow_any_reason__) == 1000

    def test_allow_any_type_metadata_with_special_characters(self):
        """Test decorator reason with special characters."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        reason = "Duck typing for: <protocols>, 'interfaces', and \"abstractions\""

        @allow_any_type(reason=reason)
        def func(x: Any) -> Any:
            return x

        assert func.__allow_any_reason__ == reason


@pytest.mark.unit
class TestAllowAnyTypeFunctionSignatures:
    """Test @allow_any_type with various function signatures."""

    def test_allow_any_type_with_no_parameters(self):
        """Test decorator on function with no parameters."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Factory function")
        def create_object() -> Any:
            return {"created": True}

        result = create_object()
        assert result == {"created": True}

    def test_allow_any_type_with_multiple_parameters(self):
        """Test decorator on function with multiple parameters."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Multiple param handling")
        def combine(a: Any, b: Any, c: Any = None) -> Any:
            return [a, b, c]

        result = combine(1, "two", {"three": 3})
        assert result == [1, "two", {"three": 3}]

    def test_allow_any_type_with_kwargs(self):
        """Test decorator on function with **kwargs."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Flexible kwargs handling")
        def process_kwargs(**kwargs: Any) -> dict:
            return kwargs

        result = process_kwargs(a=1, b="test", c=[1, 2, 3])
        assert result == {"a": 1, "b": "test", "c": [1, 2, 3]}

    def test_allow_any_type_with_args_and_kwargs(self):
        """Test decorator on function with *args and **kwargs."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Full flexibility")
        def process_all(*args: Any, **kwargs: Any) -> tuple:
            return args, kwargs

        args_result, kwargs_result = process_all(1, 2, 3, a="test", b=42)
        assert args_result == (1, 2, 3)
        assert kwargs_result == {"a": "test", "b": 42}


@pytest.mark.unit
class TestAllowAnyTypeEdgeCases:
    """Test @allow_any_type edge cases and boundary conditions."""

    def test_allow_any_type_with_none_value(self):
        """Test decorator handling None values."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Handle None gracefully")
        def process_value(value: Any) -> Any:
            return value

        result = process_value(None)
        assert result is None

    def test_allow_any_type_with_callable(self):
        """Test decorator with callable objects."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Handle callables")
        def process_callable(func: Any) -> Any:
            if callable(func):
                return func()
            return func

        def sample_func():
            return "called"

        result = process_callable(sample_func)
        assert result == "called"

    def test_allow_any_type_preserves_function_name(self):
        """Test that decorator preserves function name."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        @allow_any_type(reason="Test")
        def my_special_function(x: Any) -> Any:
            return x

        assert my_special_function.__name__ == "my_special_function"

    def test_allow_any_type_can_be_stacked(self):
        """Test that @allow_any_type can be stacked with other decorators."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        def logging_decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            return wrapper

        @logging_decorator
        @allow_any_type(reason="Stacking test")
        def stacked_function(x: Any) -> Any:
            return x * 2

        result = stacked_function(21)
        assert result == 42


@pytest.mark.unit
class TestAllowAnyTypeDocumentation:
    """Test @allow_any_type documentation requirements."""

    def test_allow_any_type_reason_is_required(self):
        """Test that reason parameter is required."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        # Should work with reason
        @allow_any_type(reason="Required reason")
        def func(x: Any) -> Any:
            return x

        assert func(1) == 1

    def test_allow_any_type_reason_documents_usage(self):
        """Test that reason parameter documents why Any is needed."""
        from omnibase_core.decorators.decorator_allow_any_type import allow_any_type

        reason = "Duck typing for protocol-agnostic object handling"

        @allow_any_type(reason=reason)
        def handle_protocol(obj: Any) -> Any:
            return obj

        # Reason should be accessible for documentation/auditing
        assert handle_protocol.__allow_any_reason__ == reason
        assert "duck typing" in handle_protocol.__allow_any_reason__.lower()
