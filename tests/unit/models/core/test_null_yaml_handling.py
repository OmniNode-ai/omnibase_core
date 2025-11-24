"""Tests for null YAML value handling in ModelMixinMetadataCollection.

MINOR-5: Handle null YAML Values in ModelMixinMetadataCollection

This test suite verifies that null/None values in YAML files are properly
normalized to sensible defaults:
- null dicts become {}
- null lists become []
- Proper type validation is applied

See: src/omnibase_core/models/core/model_mixin_metadata_collection.py
Lines: ~90-103 (code_patterns), ~111-127 (performance)
"""

import re
from pathlib import Path

import pytest

from omnibase_core.models.core.model_mixin_metadata_collection import (
    ModelMixinMetadataCollection,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestNullCodePatterns:
    """Test null code_patterns value handling."""

    def test_null_code_patterns_creates_empty_object(self, tmp_path: Path) -> None:
        """Test that null code_patterns value is normalized to empty object."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns:
"""
        yaml_file = tmp_path / "test_null_code_patterns.yaml"
        yaml_file.write_text(yaml_content)

        # Should load without error
        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        assert collection.get_mixin_count() == 1

        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        # code_patterns should be created with defaults
        assert mixin.code_patterns is not None
        assert mixin.code_patterns.inheritance == ""
        assert mixin.code_patterns.initialization == ""
        assert mixin.code_patterns.methods == []
        assert mixin.code_patterns.properties == []

    def test_null_code_patterns_methods(self, tmp_path: Path) -> None:
        """Test that null methods list in code_patterns is normalized."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    inheritance: "class MyClass:"
    initialization: "pass"
    methods:
    properties:
"""
        yaml_file = tmp_path / "test_null_methods.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        assert mixin.code_patterns is not None
        assert mixin.code_patterns.methods == []
        assert mixin.code_patterns.properties == []

    def test_invalid_code_patterns_type_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid code_patterns type raises validation error."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns: "invalid string value"
"""
        yaml_file = tmp_path / "test_invalid_code_patterns_type.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError, match=f"code_patterns.*{re.escape('must be a mapping')}"
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_methods_type_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid methods type in code_patterns raises error."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    inheritance: "class MyClass:"
    methods: "invalid string value"
"""
        yaml_file = tmp_path / "test_invalid_methods_type.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match=f"{re.escape('code_patterns.methods')}.*{re.escape('must be a list')}",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_properties_type_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid properties type in code_patterns raises error."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    inheritance: "class MyClass:"
    properties: "invalid string value"
"""
        yaml_file = tmp_path / "test_invalid_properties_type.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match=f"{re.escape('code_patterns.properties')}.*{re.escape('must be a list')}",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)


class TestNullPerformance:
    """Test null performance value handling."""

    def test_null_performance_creates_empty_object(self, tmp_path: Path) -> None:
        """Test that null performance value is normalized to empty object."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  performance:
"""
        yaml_file = tmp_path / "test_null_performance.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        assert collection.get_mixin_count() == 1

        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        # performance should be created with defaults
        assert mixin.performance is not None
        assert mixin.performance.overhead_per_call == ""
        assert mixin.performance.memory_per_instance == ""
        assert mixin.performance.recommended_max_retries is None
        assert mixin.performance.typical_use_cases == []

    def test_null_performance_use_cases(self, tmp_path: Path) -> None:
        """Test that null typical_use_cases list is normalized."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  performance:
    overhead_per_call: "~1ms"
    memory_per_instance: "~5KB"
    recommended_max_retries: 3
    typical_use_cases:
"""
        yaml_file = tmp_path / "test_null_use_cases.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        assert mixin.performance is not None
        assert mixin.performance.typical_use_cases == []

    def test_invalid_performance_type_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid performance type raises validation error."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  performance: "invalid string value"
"""
        yaml_file = tmp_path / "test_invalid_performance_type.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError, match=f"performance.*{re.escape('must be a mapping')}"
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)

    def test_invalid_use_cases_type_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid use_cases type raises error."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  performance:
    overhead_per_call: "~1ms"
    typical_use_cases: "invalid string value"
"""
        yaml_file = tmp_path / "test_invalid_use_cases_type.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(
            ModelOnexError,
            match=f"{re.escape('performance.typical_use_cases')}.*{re.escape('must be a list')}",
        ):
            ModelMixinMetadataCollection.from_yaml(yaml_file)


class TestNullConfigSchemaAndPresets:
    """Test null config_schema and presets handling."""

    def test_null_config_schema_becomes_empty_dict(self, tmp_path: Path) -> None:
        """Test that null config_schema is normalized to empty dict."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  config_schema:
"""
        yaml_file = tmp_path / "test_null_config_schema.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        assert mixin.config_schema == {}

    def test_null_presets_becomes_empty_dict(self, tmp_path: Path) -> None:
        """Test that null presets is normalized to empty dict."""
        yaml_content = """
mixin_test:
  name: "MixinTest"
  description: "Test mixin"
  version: "1.0.0"
  category: "utility"
  presets:
"""
        yaml_file = tmp_path / "test_null_presets.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("mixin_test")
        assert mixin is not None
        assert mixin.presets == {}


class TestCompleteNullHandlingWorkflow:
    """Integration tests for complete null handling workflows."""

    def test_mixin_with_all_null_optional_fields(self, tmp_path: Path) -> None:
        """Test loading mixin with all optional fields set to null."""
        yaml_content = """
mixin_minimal:
  name: "MixinMinimal"
  description: "Minimal mixin"
  version: "1.0.0"
  category: "utility"
  code_patterns:
  performance:
  config_schema:
  presets:
  usage_examples:
  implementation_notes:
"""
        yaml_file = tmp_path / "test_all_nulls.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("mixin_minimal")

        assert mixin is not None
        assert mixin.code_patterns is not None
        assert mixin.performance is not None
        assert mixin.config_schema == {}
        assert mixin.presets == {}
        assert mixin.usage_examples == []
        assert mixin.implementation_notes == []

    def test_mixed_nulls_and_values(self, tmp_path: Path) -> None:
        """Test loading mixture of null and non-null values."""
        yaml_content = """
mixin_mixed:
  name: "MixinMixed"
  description: "Mixed values"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    inheritance: "class MyMixin:"
    methods:
    properties:
  performance:
    overhead_per_call: "~1ms"
    typical_use_cases:
  config_schema:
    enabled:
      type: "boolean"
      default: true
      description: "Enable feature"
  presets:
"""
        yaml_file = tmp_path / "test_mixed_nulls.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        mixin = collection.get_mixin("mixin_mixed")

        assert mixin is not None
        # code_patterns has inheritance set, but methods/properties are null
        assert mixin.code_patterns is not None
        assert mixin.code_patterns.inheritance == "class MyMixin:"
        assert mixin.code_patterns.methods == []
        assert mixin.code_patterns.properties == []

        # performance has overhead_per_call set, but use_cases is null
        assert mixin.performance is not None
        assert mixin.performance.overhead_per_call == "~1ms"
        assert mixin.performance.typical_use_cases == []

        # config_schema has one field, presets is null
        assert len(mixin.config_schema) == 1
        assert "enabled" in mixin.config_schema
        assert mixin.presets == {}

    def test_multiple_mixins_with_various_null_patterns(self, tmp_path: Path) -> None:
        """Test loading multiple mixins with different null patterns."""
        yaml_content = """
mixin_all_nulls:
  name: "MixinAllNulls"
  description: "All null"
  version: "1.0.0"
  category: "utility"
  code_patterns:
  performance:
  config_schema:
  presets:

mixin_all_values:
  name: "MixinAllValues"
  description: "All values"
  version: "1.0.0"
  category: "flow_control"
  code_patterns:
    inheritance: "class MyMixin:"
    initialization: "pass"
    methods:
      - name: "test"
        signature: "def test(self)"
        description: "Test method"
    properties:
  performance:
    overhead_per_call: "~1ms"
    memory_per_instance: "~5KB"
    recommended_max_retries: 5
    typical_use_cases:
      - use_case: "HTTP calls"
        recommended_config: "http"
        expected_overhead: "~2ms"
  config_schema:
    max_retries:
      type: "integer"
      default: 3
      description: "Max retries"
  presets:
    default:
      description: "Default preset"
      config:
        max_retries: 3

mixin_mixed:
  name: "MixinMixed"
  description: "Mixed"
  version: "1.0.0"
  category: "utility"
  code_patterns:
    inheritance: "class MyMixin:"
    methods:
  performance:
  config_schema:
  presets:
"""
        yaml_file = tmp_path / "test_multiple_patterns.yaml"
        yaml_file.write_text(yaml_content)

        collection = ModelMixinMetadataCollection.from_yaml(yaml_file)
        assert collection.get_mixin_count() == 3

        # All nulls
        mixin1 = collection.get_mixin("mixin_all_nulls")
        assert mixin1 is not None
        assert mixin1.code_patterns is not None
        assert mixin1.config_schema == {}

        # All values
        mixin2 = collection.get_mixin("mixin_all_values")
        assert mixin2 is not None
        assert mixin2.code_patterns is not None
        assert len(mixin2.code_patterns.methods) == 1
        assert mixin2.performance is not None
        assert len(mixin2.performance.typical_use_cases) == 1
        assert len(mixin2.config_schema) == 1
        assert len(mixin2.presets) == 1

        # Mixed
        mixin3 = collection.get_mixin("mixin_mixed")
        assert mixin3 is not None
        assert mixin3.code_patterns is not None
        assert mixin3.code_patterns.inheritance == "class MyMixin:"
        assert mixin3.code_patterns.methods == []
        assert mixin3.performance is not None
        assert mixin3.config_schema == {}
        assert mixin3.presets == {}
