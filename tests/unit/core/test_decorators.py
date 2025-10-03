"""
Tests for core decorators module.

Validates decorator functionality for model configuration including
allow_any_type and allow_dict_str_any decorators.
"""

from pydantic import BaseModel

from omnibase_core.utils.decorators import allow_any_type, allow_dict_str_any


class TestAllowAnyTypeDecorator:
    """Test allow_any_type decorator functionality."""

    def test_decorator_adds_metadata(self):
        """Test that decorator adds metadata to class."""

        @allow_any_type(reason="CLI interoperability requires flexible typing")
        class TestModel(BaseModel):
            field: object

        assert hasattr(TestModel, "_allow_any_reasons")
        assert len(TestModel._allow_any_reasons) == 1
        assert (
            TestModel._allow_any_reasons[0]
            == "CLI interoperability requires flexible typing"
        )

    def test_decorator_multiple_reasons(self):
        """Test that decorator can be applied multiple times."""

        @allow_any_type(reason="First reason")
        @allow_any_type(reason="Second reason")
        class TestModel(BaseModel):
            field1: object
            field2: object

        assert hasattr(TestModel, "_allow_any_reasons")
        assert len(TestModel._allow_any_reasons) == 2
        assert "First reason" in TestModel._allow_any_reasons
        assert "Second reason" in TestModel._allow_any_reasons

    def test_decorator_preserves_model_functionality(self):
        """Test that decorator doesn't break model functionality."""

        @allow_any_type(reason="Test reason")
        class TestModel(BaseModel):
            name: str
            value: int

        # Model should work normally
        instance = TestModel(name="test", value=42)
        assert instance.name == "test"
        assert instance.value == 42

    def test_decorator_with_empty_reason(self):
        """Test decorator with empty reason string."""

        @allow_any_type(reason="")
        class TestModel(BaseModel):
            field: object

        assert hasattr(TestModel, "_allow_any_reasons")
        assert TestModel._allow_any_reasons[0] == ""

    def test_decorator_reason_parameter_required(self):
        """Test that reason parameter is properly used."""

        @allow_any_type(reason="This is a test reason for documentation")
        class TestModel(BaseModel):
            any_field: object

        assert "This is a test reason for documentation" in TestModel._allow_any_reasons


class TestAllowDictStrAnyDecorator:
    """Test allow_dict_str_any decorator functionality."""

    def test_decorator_adds_metadata(self):
        """Test that decorator adds metadata to class."""

        @allow_dict_str_any(reason="External API responses use flexible dict structure")
        class TestModel(BaseModel):
            data: dict[str, object]

        assert hasattr(TestModel, "_allow_dict_str_any_reasons")
        assert len(TestModel._allow_dict_str_any_reasons) == 1
        assert (
            TestModel._allow_dict_str_any_reasons[0]
            == "External API responses use flexible dict structure"
        )

    def test_decorator_multiple_reasons(self):
        """Test that decorator can be applied multiple times."""

        @allow_dict_str_any(reason="First reason")
        @allow_dict_str_any(reason="Second reason")
        class TestModel(BaseModel):
            field1: dict[str, object]
            field2: dict[str, object]

        assert hasattr(TestModel, "_allow_dict_str_any_reasons")
        assert len(TestModel._allow_dict_str_any_reasons) == 2
        assert "First reason" in TestModel._allow_dict_str_any_reasons
        assert "Second reason" in TestModel._allow_dict_str_any_reasons

    def test_decorator_preserves_model_functionality(self):
        """Test that decorator doesn't break model functionality."""

        @allow_dict_str_any(reason="Test reason")
        class TestModel(BaseModel):
            name: str
            metadata: dict[str, object]

        # Model should work normally
        instance = TestModel(name="test", metadata={"key": "value", "count": 42})
        assert instance.name == "test"
        assert instance.metadata["key"] == "value"
        assert instance.metadata["count"] == 42

    def test_decorator_with_empty_reason(self):
        """Test decorator with empty reason string."""

        @allow_dict_str_any(reason="")
        class TestModel(BaseModel):
            data: dict[str, object]

        assert hasattr(TestModel, "_allow_dict_str_any_reasons")
        assert TestModel._allow_dict_str_any_reasons[0] == ""

    def test_decorator_reason_parameter_required(self):
        """Test that reason parameter is properly used."""

        @allow_dict_str_any(reason="Configuration files use flexible dict structure")
        class TestModel(BaseModel):
            config: dict[str, object]

        assert (
            "Configuration files use flexible dict structure"
            in TestModel._allow_dict_str_any_reasons
        )


class TestDecoratorCombination:
    """Test using both decorators together."""

    def test_both_decorators_on_same_class(self):
        """Test that both decorators can be applied to same class."""

        @allow_any_type(reason="Any type reason")
        @allow_dict_str_any(reason="Dict reason")
        class TestModel(BaseModel):
            any_field: object
            dict_field: dict[str, object]

        assert hasattr(TestModel, "_allow_any_reasons")
        assert hasattr(TestModel, "_allow_dict_str_any_reasons")
        assert len(TestModel._allow_any_reasons) == 1
        assert len(TestModel._allow_dict_str_any_reasons) == 1

    def test_decorators_independent_metadata(self):
        """Test that decorators maintain independent metadata."""

        @allow_any_type(reason="Any reason 1")
        @allow_any_type(reason="Any reason 2")
        @allow_dict_str_any(reason="Dict reason 1")
        class TestModel(BaseModel):
            field: object

        assert len(TestModel._allow_any_reasons) == 2
        assert len(TestModel._allow_dict_str_any_reasons) == 1
        assert "Any reason 1" in TestModel._allow_any_reasons
        assert "Any reason 2" in TestModel._allow_any_reasons
        assert "Dict reason 1" in TestModel._allow_dict_str_any_reasons


class TestDecoratorDocumentation:
    """Test decorator usage for documentation purposes."""

    def test_decorator_reasons_accessible_for_documentation(self):
        """Test that reasons can be accessed for generating documentation."""

        @allow_any_type(reason="CLI tool output requires flexible typing")
        @allow_dict_str_any(reason="External API responses have dynamic schema")
        class ConfigModel(BaseModel):
            tool_output: object
            api_response: dict[str, object]

        # Verify we can access reasons for documentation generation
        any_reasons = getattr(ConfigModel, "_allow_any_reasons", [])
        dict_reasons = getattr(ConfigModel, "_allow_dict_str_any_reasons", [])

        assert len(any_reasons) > 0
        assert len(dict_reasons) > 0
        assert all(isinstance(r, str) for r in any_reasons)
        assert all(isinstance(r, str) for r in dict_reasons)

    def test_decorated_class_introspection(self):
        """Test that decorated classes can be introspected."""

        @allow_any_type(reason="Test introspection")
        class TestModel(BaseModel):
            value: object

        # Check that class is still inspectable
        assert TestModel.__name__ == "TestModel"
        assert issubclass(TestModel, BaseModel)
        assert hasattr(TestModel, "_allow_any_reasons")
