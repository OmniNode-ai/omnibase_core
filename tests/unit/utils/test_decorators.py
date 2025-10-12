"""
Unit tests for core decorators.

Tests decorators for model configuration and type annotations.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from omnibase_core.utils.decorators import allow_any_type, allow_dict_str_any


class TestAllowAnyTypeDecorator:
    """Test allow_any_type decorator."""

    def test_decorator_preserves_class(self):
        """Test that decorator returns the same class."""

        @allow_any_type(reason="Testing purposes")
        class TestModel(BaseModel):
            value: int

        assert TestModel.__name__ == "TestModel"
        assert issubclass(TestModel, BaseModel)

    def test_decorator_adds_metadata(self):
        """Test that decorator adds metadata to class."""

        @allow_any_type(reason="Test reason")
        class TestModel(BaseModel):
            value: int

        assert hasattr(TestModel, "_allow_any_reasons")
        assert isinstance(TestModel._allow_any_reasons, list)
        assert "Test reason" in TestModel._allow_any_reasons

    def test_decorator_multiple_applications(self):
        """Test applying decorator multiple times."""

        @allow_any_type(reason="First reason")
        @allow_any_type(reason="Second reason")
        class TestModel(BaseModel):
            value: int

        assert len(TestModel._allow_any_reasons) == 2
        assert "First reason" in TestModel._allow_any_reasons
        assert "Second reason" in TestModel._allow_any_reasons

    def test_decorator_with_complex_model(self):
        """Test decorator with complex model."""

        @allow_any_type(reason="Complex model needs flexibility")
        class ComplexModel(BaseModel):
            field1: str
            field2: int
            field3: bool = Field(default=True)

        instance = ComplexModel(field1="test", field2=42)
        assert instance.field1 == "test"
        assert instance.field2 == 42
        assert instance.field3 is True

    def test_decorator_preserves_functionality(self):
        """Test that decorated class works normally."""

        @allow_any_type(reason="Normal usage")
        class TestModel(BaseModel):
            name: str
            count: int = 0

        instance = TestModel(name="test", count=5)
        assert instance.name == "test"
        assert instance.count == 5

        # Pydantic validation still works
        with pytest.raises(Exception):
            TestModel(name=123, count="invalid")  # type: ignore[arg-type]

    def test_decorator_without_prior_metadata(self):
        """Test decorator on class without prior metadata."""

        @allow_any_type(reason="First use")
        class NewModel(BaseModel):
            value: str

        assert hasattr(NewModel, "_allow_any_reasons")
        assert len(NewModel._allow_any_reasons) == 1

    def test_decorator_reason_parameter(self):
        """Test that reason parameter is required and used."""

        @allow_any_type(reason="Specific reason for Any usage")
        class TestModel(BaseModel):
            field: int

        assert "Specific reason for Any usage" in TestModel._allow_any_reasons

    def test_decorator_empty_reason(self):
        """Test decorator with empty reason string."""

        @allow_any_type(reason="")
        class TestModel(BaseModel):
            field: int

        assert "" in TestModel._allow_any_reasons


class TestAllowDictStrAnyDecorator:
    """Test allow_dict_str_any decorator."""

    def test_decorator_preserves_class(self):
        """Test that decorator returns the same class."""

        @allow_dict_str_any(reason="Testing purposes")
        class TestModel(BaseModel):
            value: int

        assert TestModel.__name__ == "TestModel"
        assert issubclass(TestModel, BaseModel)

    def test_decorator_adds_metadata(self):
        """Test that decorator adds metadata to class."""

        @allow_dict_str_any(reason="Test reason")
        class TestModel(BaseModel):
            value: int

        assert hasattr(TestModel, "_allow_dict_str_any_reasons")
        assert isinstance(TestModel._allow_dict_str_any_reasons, list)
        assert "Test reason" in TestModel._allow_dict_str_any_reasons

    def test_decorator_multiple_applications(self):
        """Test applying decorator multiple times."""

        @allow_dict_str_any(reason="First reason")
        @allow_dict_str_any(reason="Second reason")
        class TestModel(BaseModel):
            value: int

        assert len(TestModel._allow_dict_str_any_reasons) == 2
        assert "First reason" in TestModel._allow_dict_str_any_reasons
        assert "Second reason" in TestModel._allow_dict_str_any_reasons

    def test_decorator_with_complex_model(self):
        """Test decorator with complex model."""

        @allow_dict_str_any(reason="Complex model needs dict[str, Any]")
        class ComplexModel(BaseModel):
            field1: str
            field2: int
            field3: list[str] = Field(default_factory=list)

        instance = ComplexModel(field1="test", field2=42)
        assert instance.field1 == "test"
        assert instance.field2 == 42
        assert instance.field3 == []

    def test_decorator_preserves_functionality(self):
        """Test that decorated class works normally."""

        @allow_dict_str_any(reason="Normal usage")
        class TestModel(BaseModel):
            name: str
            data: dict[str, str] = Field(default_factory=dict)

        instance = TestModel(name="test", data={"key": "value"})
        assert instance.name == "test"
        assert instance.data == {"key": "value"}

    def test_decorator_without_prior_metadata(self):
        """Test decorator on class without prior metadata."""

        @allow_dict_str_any(reason="First use")
        class NewModel(BaseModel):
            value: str

        assert hasattr(NewModel, "_allow_dict_str_any_reasons")
        assert len(NewModel._allow_dict_str_any_reasons) == 1

    def test_decorator_reason_parameter(self):
        """Test that reason parameter is required and used."""

        @allow_dict_str_any(reason="Specific reason for dict[str, Any] usage")
        class TestModel(BaseModel):
            field: int

        assert (
            "Specific reason for dict[str, Any] usage"
            in TestModel._allow_dict_str_any_reasons
        )

    def test_decorator_empty_reason(self):
        """Test decorator with empty reason string."""

        @allow_dict_str_any(reason="")
        class TestModel(BaseModel):
            field: int

        assert "" in TestModel._allow_dict_str_any_reasons


class TestDecoratorsCombined:
    """Test using both decorators together."""

    def test_both_decorators_on_same_class(self):
        """Test applying both decorators to same class."""

        @allow_any_type(reason="Needs Any")
        @allow_dict_str_any(reason="Needs dict[str, Any]")
        class TestModel(BaseModel):
            value: int

        assert hasattr(TestModel, "_allow_any_reasons")
        assert hasattr(TestModel, "_allow_dict_str_any_reasons")
        assert "Needs Any" in TestModel._allow_any_reasons
        assert "Needs dict[str, Any]" in TestModel._allow_dict_str_any_reasons

    def test_decorators_order_independence(self):
        """Test that decorator order doesn't matter."""

        @allow_dict_str_any(reason="Dict reason")
        @allow_any_type(reason="Any reason")
        class TestModel1(BaseModel):
            value: int

        @allow_any_type(reason="Any reason")
        @allow_dict_str_any(reason="Dict reason")
        class TestModel2(BaseModel):
            value: int

        assert hasattr(TestModel1, "_allow_any_reasons")
        assert hasattr(TestModel1, "_allow_dict_str_any_reasons")
        assert hasattr(TestModel2, "_allow_any_reasons")
        assert hasattr(TestModel2, "_allow_dict_str_any_reasons")

    def test_both_decorators_preserve_functionality(self):
        """Test that both decorators preserve model functionality."""

        @allow_any_type(reason="Test")
        @allow_dict_str_any(reason="Test")
        class TestModel(BaseModel):
            name: str
            count: int = 0

        instance = TestModel(name="test", count=5)
        assert instance.name == "test"
        assert instance.count == 5

    def test_separate_metadata_lists(self):
        """Test that decorators maintain separate metadata lists."""

        @allow_any_type(reason="Any reason 1")
        @allow_any_type(reason="Any reason 2")
        @allow_dict_str_any(reason="Dict reason 1")
        @allow_dict_str_any(reason="Dict reason 2")
        class TestModel(BaseModel):
            value: int

        assert len(TestModel._allow_any_reasons) == 2
        assert len(TestModel._allow_dict_str_any_reasons) == 2
        assert "Any reason 1" in TestModel._allow_any_reasons
        assert "Dict reason 1" in TestModel._allow_dict_str_any_reasons


class TestDecoratorsEdgeCases:
    """Test edge cases and unusual usage."""

    def test_decorator_on_model_with_inheritance(self):
        """Test decorator on model with inheritance."""

        class BaseTestModel(BaseModel):
            base_field: str

        @allow_any_type(reason="Inherited model")
        class DerivedModel(BaseTestModel):
            derived_field: int

        instance = DerivedModel(base_field="test", derived_field=42)
        assert instance.base_field == "test"
        assert instance.derived_field == 42
        assert hasattr(DerivedModel, "_allow_any_reasons")

    def test_decorator_metadata_inherited(self):
        """Test that metadata IS inherited (Python class attribute behavior)."""

        @allow_any_type(reason="Base reason")
        class BaseModel1(BaseModel):
            field: int

        class DerivedModel1(BaseModel1):
            other: str

        assert hasattr(BaseModel1, "_allow_any_reasons")
        # In Python, class attributes are inherited
        assert hasattr(DerivedModel1, "_allow_any_reasons")
        # Both share the same list reference
        assert DerivedModel1._allow_any_reasons is BaseModel1._allow_any_reasons

    def test_decorator_with_model_config(self):
        """Test decorator with model_config."""

        @allow_any_type(reason="Custom config")
        class TestModel(BaseModel):
            value: int

            model_config = {"extra": "forbid", "validate_assignment": True}

        instance = TestModel(value=42)
        assert instance.value == 42
        assert hasattr(TestModel, "_allow_any_reasons")

    def test_decorator_unicode_reason(self):
        """Test decorator with unicode characters in reason."""

        @allow_any_type(reason="Unicode: 你好 мир 🌍")
        class TestModel(BaseModel):
            field: int

        assert "Unicode: 你好 мир 🌍" in TestModel._allow_any_reasons

    def test_decorator_long_reason(self):
        """Test decorator with very long reason."""
        long_reason = "A" * 1000

        @allow_any_type(reason=long_reason)
        class TestModel(BaseModel):
            field: int

        assert long_reason in TestModel._allow_any_reasons
        assert len(TestModel._allow_any_reasons[0]) == 1000

    def test_decorator_multiline_reason(self):
        """Test decorator with multiline reason."""
        reason = """This is a multiline reason.
        It explains why we need Any type.
        Multiple lines are supported."""

        @allow_any_type(reason=reason)
        class TestModel(BaseModel):
            field: int

        assert reason in TestModel._allow_any_reasons
        assert "\n" in TestModel._allow_any_reasons[0]
