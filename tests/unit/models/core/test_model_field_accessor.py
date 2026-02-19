# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for the generic field accessor pattern.

Validates that the field accessor provides proper dot notation support,
type safety, and backward compatibility with existing field access patterns.
"""

from typing import Any

import pytest
from pydantic import Field

from omnibase_core.models.core import (
    ModelCustomFieldsAccessor,
    ModelEnvironmentAccessor,
    ModelFieldAccessor,
    ModelResultAccessor,
    ModelTypedAccessor,
)


@pytest.mark.unit
class TestModelFieldAccessor:
    """Test basic field accessor functionality."""

    def test_basic_field_access(self):
        """Test basic get/set field operations."""

        @pytest.mark.unit
        class TestModel(ModelFieldAccessor):
            data: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Test setting and getting
        assert model.set_field("data.key1", "value1")
        assert model.get_field("data.key1").unwrap().to_value() == "value1"

        # Test default values
        from omnibase_core.models.common.model_schema_value import ModelSchemaValue

        default_value = ModelSchemaValue.from_value("default")
        assert (
            model.get_field("data.nonexistent", default_value).unwrap().to_value()
            == "default"
        )

        # Test has_field
        assert model.has_field("data.key1")
        assert not model.has_field("data.nonexistent")

    def test_dot_notation_nested_access(self):
        """Test nested field access with dot notation."""

        @pytest.mark.unit
        class TestModel(ModelFieldAccessor):
            config: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Set nested values
        assert model.set_field("config.database.host", "localhost")
        assert model.set_field("config.database.port", 5432)
        assert model.set_field("config.features.enabled", True)

        # Get nested values
        assert (
            model.get_field("config.database.host").unwrap().to_value() == "localhost"
        )
        assert model.get_field("config.database.port").unwrap().to_value() == 5432
        assert model.get_field("config.features.enabled").unwrap().to_value() is True

        # Test deeper nesting
        assert model.set_field("config.api.v1.endpoints.users", "/api/v1/users")
        assert (
            model.get_field("config.api.v1.endpoints.users").unwrap().to_value()
            == "/api/v1/users"
        )

    def test_remove_field(self):
        """Test field removal."""

        @pytest.mark.unit
        class TestModel(ModelFieldAccessor):
            data: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Set and remove
        model.set_field("data.temp", "temporary")
        assert model.has_field("data.temp")

        assert model.remove_field("data.temp")
        assert not model.has_field("data.temp")

        # Try to remove non-existent field
        assert not model.remove_field("data.nonexistent")

    def test_attribute_vs_dict_access(self):
        """Test accessing both model attributes and dict fields."""

        @pytest.mark.unit
        class TestModel(ModelFieldAccessor):
            name: str = "test_model"
            data: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Test attribute access
        assert model.get_field("name").unwrap().to_value() == "test_model"
        assert model.set_field("name", "updated_model")
        assert model.get_field("name").unwrap().to_value() == "updated_model"

        # Test dict field access
        assert model.set_field("data.key", "value")
        assert model.get_field("data.key").unwrap().to_value() == "value"


@pytest.mark.unit
class TestModelTypedAccessor:
    """Test typed field accessor with generic type safety."""

    def test_typed_field_access(self):
        """Test type-safe field access."""

        @pytest.mark.unit
        class TestModel(ModelTypedAccessor[str]):
            data: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Set values
        model.set_field("data.text", "hello")
        model.set_field("data.number", 42)

        # Get with type checking
        text = model.get_typed_field("data.text", str, "default")
        assert text == "hello"

        # Wrong type should return default
        text_from_number = model.get_typed_field("data.number", str, "default")
        assert text_from_number == "default"

        # Correct type should work
        number = model.get_typed_field("data.number", int, 0)
        assert number == 42

    def test_set_typed_field(self):
        """Test typed field setting with validation."""

        @pytest.mark.unit
        class TestModel(ModelTypedAccessor[str]):
            data: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Valid type should work
        assert model.set_typed_field("data.text", "hello", str)
        assert model.get_field("data.text").unwrap().to_value() == "hello"

        # Invalid type should fail
        assert not model.set_typed_field("data.text", 42, str)


@pytest.mark.unit
class TestModelEnvironmentAccessor:
    """Test environment accessor with type coercion."""

    def test_string_coercion(self):
        """Test string value coercion."""

        @pytest.mark.unit
        class TestModel(ModelEnvironmentAccessor):
            props: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        model.set_field("props.string_val", "hello")
        model.set_field("props.int_val", 42)
        model.set_field("props.bool_val", True)

        assert model.get_string("props.string_val") == "hello"
        assert model.get_string("props.int_val") == "42"
        assert model.get_string("props.bool_val") == "True"
        assert model.get_string("props.nonexistent", "default") == "default"

    def test_int_coercion(self):
        """Test integer value coercion."""

        @pytest.mark.unit
        class TestModel(ModelEnvironmentAccessor):
            props: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        model.set_field("props.int_val", 42)
        model.set_field("props.float_val", 42.7)
        model.set_field("props.string_num", "123")
        model.set_field("props.string_text", "hello")

        assert model.get_int("props.int_val") == 42
        assert model.get_int("props.float_val") == 42
        assert model.get_int("props.string_num") == 123
        assert model.get_int("props.string_text", 99) == 99  # default
        assert model.get_int("props.nonexistent", 99) == 99

    def test_bool_coercion(self):
        """Test boolean value coercion."""

        @pytest.mark.unit
        class TestModel(ModelEnvironmentAccessor):
            props: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        model.set_field("props.bool_true", True)
        model.set_field("props.bool_false", False)
        model.set_field("props.string_true", "true")
        model.set_field("props.string_yes", "yes")
        model.set_field("props.string_1", "1")
        model.set_field("props.string_false", "false")
        model.set_field("props.int_1", 1)
        model.set_field("props.int_0", 0)

        assert model.get_bool("props.bool_true") is True
        assert model.get_bool("props.bool_false") is False
        assert model.get_bool("props.string_true") is True
        assert model.get_bool("props.string_yes") is True
        assert model.get_bool("props.string_1") is True
        assert model.get_bool("props.string_false") is False
        assert model.get_bool("props.int_1") is True
        assert model.get_bool("props.int_0") is False

    def test_list_coercion(self):
        """Test list value coercion."""

        @pytest.mark.unit
        class TestModel(ModelEnvironmentAccessor):
            props: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        model.set_field("props.list_val", ["a", "b", "c"])
        model.set_field("props.csv_string", "x,y,z")
        model.set_field("props.mixed_list", [1, 2, 3])

        assert model.get_list("props.list_val") == ["a", "b", "c"]
        assert model.get_list("props.csv_string") == ["x", "y", "z"]
        assert model.get_list("props.mixed_list") == ["1", "2", "3"]
        assert model.get_list("props.nonexistent", ["default"]) == ["default"]


@pytest.mark.unit
class TestModelResultAccessor:
    """Test CLI result accessor functionality."""

    def test_result_value_access(self):
        """Test getting values from results and metadata."""

        @pytest.mark.unit
        class TestModel(ModelResultAccessor):
            results: dict[str, Any] = Field(default_factory=dict)
            metadata: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Set values in results and metadata
        model.set_field("results.exit_code", 0)
        model.set_field("metadata.duration_ms", 150.5)

        # Test result value access (checks both results and metadata)
        assert model.get_result_value("exit_code") == 0
        assert model.get_result_value("duration_ms") == 150.5
        assert model.get_result_value("nonexistent", "default") == "default"

    def test_set_result_and_metadata(self):
        """Test setting result and metadata values."""

        @pytest.mark.unit
        class TestModel(ModelResultAccessor):
            results: dict[str, Any] = Field(default_factory=dict)
            metadata: dict[str, Any] = Field(default_factory=dict)

        model = TestModel()

        # Test setting result values
        assert model.set_result_value("exit_code", 0)
        assert model.get_field("results.exit_code").unwrap().to_value() == 0

        # Test setting metadata values
        assert model.set_metadata_value("timestamp", "2024-01-01T12:00:00")
        assert (
            model.get_field("metadata.timestamp").unwrap().to_value()
            == "2024-01-01T12:00:00"
        )


@pytest.mark.unit
class TestModelCustomFieldsAccessor:
    """Test custom fields accessor functionality."""

    def test_custom_field_access(self):
        """Test custom field operations."""

        @pytest.mark.unit
        class TestModel(ModelCustomFieldsAccessor):
            custom_fields: dict[str, Any] | None = Field(default=None)

        model = TestModel()

        # Initially no custom fields
        assert not model.has_custom_field("key1")
        assert model.get_custom_field("key1", "default") == "default"

        # Set custom field (should initialize custom_fields)
        assert model.set_custom_field("key1", "value1")
        assert model.has_custom_field("key1")
        assert model.get_custom_field("key1") == "value1"

        # Remove custom field
        assert model.remove_custom_field("key1")
        assert not model.has_custom_field("key1")

    def test_custom_fields_initialization(self):
        """Test that custom_fields dict is properly initialized."""

        @pytest.mark.unit
        class TestModel(ModelCustomFieldsAccessor):
            custom_fields: dict[str, Any] | None = Field(default=None)

        model = TestModel()

        # Should be None initially
        assert model.custom_fields is None

        # Setting a field should initialize it
        model.set_custom_field("test", "value")
        assert model.custom_fields is not None
        assert model.custom_fields == {"test": "value"}


@pytest.mark.unit
class TestFieldAccessorIntegration:
    """Test integration scenarios with real-world usage patterns."""

    def test_cli_output_data_pattern(self):
        """Test CLI output data access pattern."""

        class CliOutputData(ModelResultAccessor):
            output_type: str = "execution"
            results: dict[str, Any] = Field(default_factory=dict)
            metadata: dict[str, Any] = Field(default_factory=dict)
            files_created: list[str] = Field(default_factory=list)

        cli_data = CliOutputData()

        # Use both direct field access and result accessor methods
        cli_data.set_result_value("exit_code", 0)
        cli_data.set_metadata_value("duration_ms", 250.3)
        cli_data.set_field("files_created", ["output.txt", "log.txt"])

        # Access using different methods
        assert cli_data.get_result_value("exit_code") == 0
        assert cli_data.get_field("metadata.duration_ms").unwrap().to_value() == 250.3
        assert cli_data.get_field("files_created").unwrap().to_value() == [
            "output.txt",
            "log.txt",
        ]

    def test_environment_properties_pattern(self):
        """Test environment properties access pattern."""

        class EnvironmentProperties(ModelEnvironmentAccessor):
            properties: dict[str, Any] = Field(default_factory=dict)

        env_props = EnvironmentProperties()

        # Set various types of properties
        env_props.set_field("properties.database.host", "localhost")
        env_props.set_field("properties.database.port", "5432")
        env_props.set_field("properties.debug", "true")
        env_props.set_field("properties.features", "auth,logging,metrics")

        # Access with type coercion
        host = env_props.get_string("properties.database.host")
        port = env_props.get_int("properties.database.port")
        debug = env_props.get_bool("properties.debug")
        features = env_props.get_list("properties.features")

        assert host == "localhost"
        assert port == 5432
        assert debug is True
        assert features == ["auth", "logging", "metrics"]

    def test_generic_metadata_pattern(self):
        """Test generic metadata access pattern."""

        class GenericMetadata(ModelCustomFieldsAccessor):
            name: str | None = None
            custom_fields: dict[str, Any] | None = Field(default=None)

        metadata = GenericMetadata()
        metadata.name = "test_metadata"

        # Use custom fields accessor
        metadata.set_custom_field("version", "1.0.0")
        metadata.set_custom_field("author", "team@company.com")

        # Use dot notation for nested custom fields
        metadata.set_field("custom_fields.build.number", 42)
        metadata.set_field("custom_fields.build.timestamp", "2024-01-01T12:00:00")

        # Access using different methods
        assert metadata.get_custom_field("version") == "1.0.0"
        assert (
            metadata.get_field("custom_fields.build.number").unwrap().to_value() == 42
        )
        assert metadata.has_custom_field("author")
        assert metadata.has_field("custom_fields.build.timestamp")
