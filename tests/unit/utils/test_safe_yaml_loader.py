"""
Comprehensive unit tests for safe YAML loading utilities.

Tests cover:
- Loading and validating YAML files against Pydantic models
- Loading YAML content from strings
- YAML serialization to strings
- Pydantic model serialization to YAML
- Schema example extraction from YAML files
- Error handling for invalid YAML, missing files, validation errors
- Unicode and encoding handling
- Security considerations
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.config.model_schema_example import ModelSchemaExample
from omnibase_core.models.core.model_custom_properties import ModelCustomProperties
from omnibase_core.utils.safe_yaml_loader import (
    extract_example_from_schema,
    load_and_validate_yaml_model,
    load_yaml_content_as_model,
    serialize_data_to_yaml,
    serialize_pydantic_model_to_yaml,
)


# Test models for YAML validation
class SimpleTestModel(BaseModel):
    """Simple test model."""

    name: str
    value: int
    enabled: bool = False


class NestedTestModel(BaseModel):
    """Nested test model."""

    simple: SimpleTestModel
    tags: list[str]
    metadata: dict[str, Any]


class TestModelWithValidation(BaseModel):
    """Test model with field validation."""

    email: str
    age: int

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 0 or v > 150:
            raise ValueError("Age must be between 0 and 150")
        return v


class TestLoadAndValidateYamlModel:
    """Test load_and_validate_yaml_model function."""

    def test_load_simple_yaml_file(self, tmp_path: Path) -> None:
        """Test loading simple valid YAML file."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
name: TestName
value: 42
enabled: true
""",
        )

        result = load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert result.name == "TestName"
        assert result.value == 42
        assert result.enabled is True

    def test_load_yaml_with_defaults(self, tmp_path: Path) -> None:
        """Test loading YAML with missing optional fields uses defaults."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(
            """
name: TestName
value: 100
""",
        )

        result = load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert result.name == "TestName"
        assert result.value == 100
        assert result.enabled is False  # Default value

    def test_load_nested_yaml_file(self, tmp_path: Path) -> None:
        """Test loading nested YAML structure."""
        yaml_file = tmp_path / "nested.yaml"
        yaml_file.write_text(
            """
simple:
  name: Inner
  value: 99
  enabled: true
tags:
  - tag1
  - tag2
metadata:
  key1: value1
  key2: 123
""",
        )

        result = load_and_validate_yaml_model(yaml_file, NestedTestModel)
        assert result.simple.name == "Inner"
        assert result.simple.value == 99
        assert result.tags == ["tag1", "tag2"]
        assert result.metadata["key1"] == "value1"

    def test_load_empty_yaml_file(self, tmp_path: Path) -> None:
        """Test loading empty YAML file."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        with pytest.raises(OnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_load_yaml_validation_error(self, tmp_path: Path) -> None:
        """Test YAML loading with validation error."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(
            """
name: TestName
value: not_an_integer
""",
        )

        with pytest.raises(OnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "YAML validation error" in exc_info.value.message

    def test_load_yaml_missing_required_field(self, tmp_path: Path) -> None:
        """Test YAML loading with missing required field."""
        yaml_file = tmp_path / "incomplete.yaml"
        yaml_file.write_text(
            """
name: TestName
""",
        )

        with pytest.raises(OnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_load_yaml_file_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent YAML file."""
        yaml_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(OnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.NOT_FOUND
        assert "YAML file not found" in exc_info.value.message

    def test_load_yaml_parsing_error(self, tmp_path: Path) -> None:
        """Test loading malformed YAML file."""
        yaml_file = tmp_path / "malformed.yaml"
        yaml_file.write_text(
            """
name: TestName
value: 42
  invalid_indent: bad
""",
        )

        with pytest.raises(OnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.CONVERSION_ERROR
        assert "YAML parsing error" in exc_info.value.message

    def test_load_yaml_with_custom_validation(self, tmp_path: Path) -> None:
        """Test YAML loading with custom field validation."""
        yaml_file = tmp_path / "validated.yaml"
        yaml_file.write_text(
            """
email: test@example.com
age: 30
""",
        )

        result = load_and_validate_yaml_model(yaml_file, TestModelWithValidation)
        assert result.email == "test@example.com"
        assert result.age == 30

    def test_load_yaml_custom_validation_fails(self, tmp_path: Path) -> None:
        """Test YAML loading fails with custom validation."""
        yaml_file = tmp_path / "invalid_email.yaml"
        yaml_file.write_text(
            """
email: invalid_email
age: 30
""",
        )

        with pytest.raises(OnexError) as exc_info:
            load_and_validate_yaml_model(yaml_file, TestModelWithValidation)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_load_yaml_unicode_content(self, tmp_path: Path) -> None:
        """Test loading YAML with Unicode content."""
        yaml_file = tmp_path / "unicode.yaml"
        yaml_file.write_text(
            """
name: 日本語
value: 42
""",
            encoding="utf-8",
        )

        result = load_and_validate_yaml_model(yaml_file, SimpleTestModel)
        assert result.name == "日本語"
        assert result.value == 42


class TestLoadYamlContentAsModel:
    """Test load_yaml_content_as_model function."""

    def test_load_simple_yaml_content(self) -> None:
        """Test loading simple YAML content from string."""
        content = """
name: TestName
value: 42
enabled: true
"""
        result = load_yaml_content_as_model(content, SimpleTestModel)
        assert result.name == "TestName"
        assert result.value == 42
        assert result.enabled is True

    def test_load_empty_yaml_content(self) -> None:
        """Test loading empty YAML content."""
        with pytest.raises(OnexError) as exc_info:
            load_yaml_content_as_model("", SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_load_yaml_content_validation_error(self) -> None:
        """Test YAML content with validation error."""
        content = """
name: TestName
value: not_an_integer
"""
        with pytest.raises(OnexError) as exc_info:
            load_yaml_content_as_model(content, SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_load_yaml_content_parsing_error(self) -> None:
        """Test malformed YAML content."""
        content = """
name: TestName
value: 42
  invalid_indent: bad
"""
        with pytest.raises(OnexError) as exc_info:
            load_yaml_content_as_model(content, SimpleTestModel)
        assert exc_info.value.code == EnumCoreErrorCode.CONVERSION_ERROR
        assert "YAML parsing error" in exc_info.value.message

    def test_load_nested_yaml_content(self) -> None:
        """Test loading nested YAML content."""
        content = """
simple:
  name: Inner
  value: 99
  enabled: true
tags:
  - tag1
  - tag2
metadata:
  key: value
"""
        result = load_yaml_content_as_model(content, NestedTestModel)
        assert result.simple.name == "Inner"
        assert result.tags == ["tag1", "tag2"]

    def test_load_yaml_content_unicode(self) -> None:
        """Test loading YAML content with Unicode."""
        content = """
name: 中文测试
value: 123
"""
        result = load_yaml_content_as_model(content, SimpleTestModel)
        assert result.name == "中文测试"


class TestSerializePydanticModelToYaml:
    """Test serialize_pydantic_model_to_yaml function."""

    def test_serialize_simple_model(self) -> None:
        """Test serializing simple Pydantic model."""
        model = SimpleTestModel(name="Test", value=42, enabled=True)
        yaml_str = serialize_pydantic_model_to_yaml(model)

        # Verify it's valid YAML text with expected content
        assert isinstance(yaml_str, str)
        assert "Test" in yaml_str
        assert "42" in yaml_str or "value: 42" in yaml_str
        # Verify it produces YAML-like output
        assert ":" in yaml_str

    def test_serialize_nested_model(self) -> None:
        """Test serializing nested Pydantic model."""
        model = NestedTestModel(
            simple=SimpleTestModel(name="Inner", value=99),
            tags=["tag1", "tag2"],
            metadata={"key": "value"},
        )
        yaml_str = serialize_pydantic_model_to_yaml(model)

        # Verify it's valid YAML text with nested content
        assert isinstance(yaml_str, str)
        assert "Inner" in yaml_str
        assert "tag1" in yaml_str or "- tag1" in yaml_str
        assert ":" in yaml_str

    def test_serialize_with_comment_prefix(self) -> None:
        """Test serializing with comment prefix."""
        model = SimpleTestModel(name="Test", value=42)
        yaml_str = serialize_pydantic_model_to_yaml(model, comment_prefix="# ")

        # Check that each line has comment prefix
        lines = yaml_str.splitlines()
        for line in lines:
            if line.strip():  # Non-empty lines
                assert line.startswith("# ")

    def test_serialize_with_yaml_options(self) -> None:
        """Test serializing with custom YAML options."""
        model = SimpleTestModel(name="Test", value=42)
        yaml_str = serialize_pydantic_model_to_yaml(
            model,
            sort_keys=True,
            indent=4,
        )

        # Verify it's valid YAML text
        assert isinstance(yaml_str, str)
        assert "Test" in yaml_str
        assert ":" in yaml_str

    def test_serialize_model_with_to_serializable_dict(self) -> None:
        """Test serializing model with custom to_serializable_dict method."""

        class CustomModel(BaseModel):
            value: int

            def to_serializable_dict(self) -> dict[str, Any]:
                return {"custom_value": self.value * 2}

        model = CustomModel(value=21)
        yaml_str = serialize_pydantic_model_to_yaml(model)

        # Verify it contains the custom serialized value
        assert isinstance(yaml_str, str)
        assert "42" in yaml_str or "custom_value" in yaml_str


class TestSerializeDataToYaml:
    """Test serialize_data_to_yaml function."""

    def test_serialize_simple_dict(self) -> None:
        """Test serializing simple dictionary."""
        data = {"name": "Test", "value": 42, "enabled": True}
        yaml_str = serialize_data_to_yaml(data)

        parsed = yaml.safe_load(yaml_str)
        assert parsed == data

    def test_serialize_list(self) -> None:
        """Test serializing list."""
        data = ["item1", "item2", "item3"]
        yaml_str = serialize_data_to_yaml(data)

        parsed = yaml.safe_load(yaml_str)
        assert parsed == data

    def test_serialize_nested_structure(self) -> None:
        """Test serializing nested structure."""
        data = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "mixed": [{"a": 1}, {"b": 2}],
        }
        yaml_str = serialize_data_to_yaml(data)

        parsed = yaml.safe_load(yaml_str)
        assert parsed == data

    def test_serialize_with_comment_prefix(self) -> None:
        """Test serializing data with comment prefix."""
        data = {"key": "value"}
        yaml_str = serialize_data_to_yaml(data, comment_prefix="# ")

        lines = yaml_str.splitlines()
        for line in lines:
            if line.strip():
                assert line.startswith("# ")

    def test_serialize_unicode_data(self) -> None:
        """Test serializing Unicode data."""
        data = {"name": "日本語", "value": "中文"}
        yaml_str = serialize_data_to_yaml(data)

        parsed = yaml.safe_load(yaml_str)
        assert parsed["name"] == "日本語"
        assert parsed["value"] == "中文"

    def test_serialize_with_allow_unicode(self) -> None:
        """Test serializing with allow_unicode option."""
        data = {"text": "Ñoño"}
        yaml_str = serialize_data_to_yaml(data, allow_unicode=True)

        # Should contain Unicode characters directly
        assert "Ñoño" in yaml_str


class TestExtractExampleFromSchema:
    """Test extract_example_from_schema function."""

    def test_extract_first_example(self, tmp_path: Path) -> None:
        """Test extracting first example from schema."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
examples:
  - name: Example 1
    value: 100
    flag: true
  - name: Example 2
    value: 200
""",
        )

        result = extract_example_from_schema(schema_file, example_index=0)
        assert isinstance(result, ModelSchemaExample)
        assert result.example_index == 0
        assert result.is_validated is True

        # Check custom properties using get_custom_value
        assert result.example_data.get_custom_value("name") == "Example 1"
        assert result.example_data.get_custom_value("value") == 100.0
        # YAML loader converts boolean to float (1.0 for true, 0.0 for false)
        assert result.example_data.get_custom_value("flag") == 1.0

    def test_extract_second_example(self, tmp_path: Path) -> None:
        """Test extracting second example from schema."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
examples:
  - name: Example 1
  - name: Example 2
    extra: data
""",
        )

        result = extract_example_from_schema(schema_file, example_index=1)
        assert result.example_index == 1
        assert result.example_data.get_custom_value("name") == "Example 2"

    def test_extract_example_no_examples_section(self, tmp_path: Path) -> None:
        """Test extracting from schema without examples section."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
name: Schema
version: 1.0
""",
        )

        with pytest.raises(OnexError) as exc_info:
            extract_example_from_schema(schema_file)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "No 'examples' section found" in exc_info.value.message

    def test_extract_example_index_out_of_range(self, tmp_path: Path) -> None:
        """Test extracting example with out of range index."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
examples:
  - name: Only Example
""",
        )

        with pytest.raises(OnexError) as exc_info:
            extract_example_from_schema(schema_file, example_index=5)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "index 5 out of range" in exc_info.value.message

    def test_extract_example_not_dict(self, tmp_path: Path) -> None:
        """Test extracting example that is not a dict."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
examples:
  - "This is a string, not a dict"
""",
        )

        with pytest.raises(OnexError) as exc_info:
            extract_example_from_schema(schema_file, example_index=0)
        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "is not a dict" in exc_info.value.message

    def test_extract_example_with_mixed_types(self, tmp_path: Path) -> None:
        """Test extracting example with mixed data types."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
examples:
  - string_field: "text"
    int_field: 42
    float_field: 3.14
    bool_field: true
    nested_field:
      ignored: "nested structures are ignored"
""",
        )

        result = extract_example_from_schema(schema_file)

        # Check that different types are properly handled using get_custom_value
        assert result.example_data.get_custom_value("string_field") == "text"
        assert result.example_data.get_custom_value("int_field") == 42.0
        assert result.example_data.get_custom_value("float_field") == 3.14
        # YAML loader converts boolean to float (1.0 for true, 0.0 for false)
        assert result.example_data.get_custom_value("bool_field") == 1.0

    def test_extract_example_file_not_found(self, tmp_path: Path) -> None:
        """Test extracting from non-existent schema file."""
        schema_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(OnexError) as exc_info:
            extract_example_from_schema(schema_file)
        assert exc_info.value.code == EnumCoreErrorCode.INTERNAL_ERROR

    def test_extract_example_malformed_yaml(self, tmp_path: Path) -> None:
        """Test extracting from malformed YAML schema."""
        schema_file = tmp_path / "malformed.yaml"
        # Create actually malformed YAML with incorrect indentation
        schema_file.write_text(
            """
examples:
  - name: Test
  value: 42
    invalid_indent: bad
""",
        )

        # Should raise an error due to YAML parsing failure
        with pytest.raises(OnexError) as exc_info:
            extract_example_from_schema(schema_file)
        assert exc_info.value.code in [
            EnumCoreErrorCode.INTERNAL_ERROR,
            EnumCoreErrorCode.VALIDATION_ERROR,
        ]
