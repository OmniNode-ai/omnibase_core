"""Comprehensive tests for null YAML value handling in ModelMixinMetadataCollection.

Tests cover MINOR-5 issue: graceful handling of null YAML values with
proper normalization and validation.
"""

from pathlib import Path

import pytest

from omnibase_core.models.core.model_mixin_metadata_collection import (
    ModelMixinMetadataCollection,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestNullValueHandling:
    """Test graceful handling of null YAML values (MINOR-5)."""

    def test_load_yaml_with_null_code_patterns(self, tmp_path: Path) -> None:
        """Test loading YAML with null code_patterns normalizes to empty model."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin with null code_patterns"
  version: "1.0.0"
  category: "utility"
  code_patterns: null
"""
        yaml_file = tmp_path / "test_null_code_patterns.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("test_mixin")

        assert mixin is not None
        assert mixin.code_patterns is not None
        assert mixin.code_patterns.inheritance == ""
        assert mixin.code_patterns.methods == []
        assert mixin.code_patterns.properties == []

    def test_load_yaml_with_null_presets(self, tmp_path: Path) -> None:
        """Test loading YAML with null presets normalizes to empty dict."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin with null presets"
  version: "1.0.0"
  category: "utility"
  presets: null
"""
        yaml_file = tmp_path / "test_null_presets.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("test_mixin")

        assert mixin is not None
        assert mixin.presets == {}

    def test_load_yaml_with_null_performance(self, tmp_path: Path) -> None:
        """Test loading YAML with null performance normalizes to empty model."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin with null performance"
  version: "1.0.0"
  category: "utility"
  performance: null
"""
        yaml_file = tmp_path / "test_null_performance.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("test_mixin")

        assert mixin is not None
        assert mixin.performance is not None
        assert mixin.performance.typical_use_cases == []

    def test_load_yaml_with_null_config_schema(self, tmp_path: Path) -> None:
        """Test loading YAML with null config_schema normalizes to empty dict."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin with null config_schema"
  version: "1.0.0"
  category: "utility"
  config_schema: null
"""
        yaml_file = tmp_path / "test_null_config_schema.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("test_mixin")

        assert mixin is not None
        assert mixin.config_schema == {}

    def test_load_yaml_with_null_nested_methods(self, tmp_path: Path) -> None:
        """Test loading YAML with null code_patterns.methods normalizes to empty list."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin with null methods"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    inheritance: "class Mixin:"
    methods: null
    properties: null
"""
        yaml_file = tmp_path / "test_null_nested.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("test_mixin")

        assert mixin is not None
        assert mixin.code_patterns is not None
        assert mixin.code_patterns.inheritance == "class Mixin:"
        assert mixin.code_patterns.methods == []
        assert mixin.code_patterns.properties == []

    def test_load_yaml_with_null_performance_use_cases(self, tmp_path: Path) -> None:
        """Test loading YAML with null performance.typical_use_cases normalizes to empty list."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin with null use cases"
  version: "1.0.0"
  category: "utility"
  performance:
    overhead_per_call: "~1ms"
    typical_use_cases: null
"""
        yaml_file = tmp_path / "test_null_use_cases.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("test_mixin")

        assert mixin is not None
        assert mixin.performance is not None
        assert mixin.performance.typical_use_cases == []
        assert mixin.performance.overhead_per_call == "~1ms"


class TestInvalidTypeValidation:
    """Test validation of invalid types raises proper errors."""

    def test_invalid_code_patterns_type_raises_error(self, tmp_path: Path) -> None:
        """Test invalid code_patterns type raises ModelOnexError."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns: "invalid_string"
"""
        yaml_file = tmp_path / "test_invalid_code_patterns.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match="code_patterns for mixin 'test_mixin' must be a mapping",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_methods_type_raises_error(self, tmp_path: Path) -> None:
        """Test invalid code_patterns.methods type raises ModelOnexError."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    methods: "invalid_string"
"""
        yaml_file = tmp_path / "test_invalid_methods.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match="code_patterns.methods for mixin 'test_mixin' must be a list",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_properties_type_raises_error(self, tmp_path: Path) -> None:
        """Test invalid code_patterns.properties type raises ModelOnexError."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    properties: "invalid_string"
"""
        yaml_file = tmp_path / "test_invalid_properties.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match="code_patterns.properties for mixin 'test_mixin' must be a list",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_config_schema_type_raises_error(self, tmp_path: Path) -> None:
        """Test invalid config_schema type raises ModelOnexError."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  config_schema: "invalid_string"
"""
        yaml_file = tmp_path / "test_invalid_config_schema.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match="config_schema for mixin 'test_mixin' must be a mapping",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_presets_type_raises_error(self, tmp_path: Path) -> None:
        """Test invalid presets type raises ModelOnexError."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  presets: "invalid_string"
"""
        yaml_file = tmp_path / "test_invalid_presets.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match="presets for mixin 'test_mixin' must be a mapping",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_performance_type_raises_error(self, tmp_path: Path) -> None:
        """Test invalid performance type raises ModelOnexError."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  performance: "invalid_string"
"""
        yaml_file = tmp_path / "test_invalid_performance.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match="performance for mixin 'test_mixin' must be a mapping",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_performance_use_cases_type_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Test invalid performance.typical_use_cases type raises ModelOnexError."""
        yaml_content = """
test_mixin:
  name: "TestMixin"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  performance:
    overhead_per_call: "~1ms"
    typical_use_cases: "invalid_string"
"""
        yaml_file = tmp_path / "test_invalid_use_cases.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match="performance.typical_use_cases for mixin 'test_mixin' must be a list",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)
