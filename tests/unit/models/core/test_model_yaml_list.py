"""
Tests for ModelYamlList.

Comprehensive tests for YAML list model including initialization,
list handling, and edge cases.
"""

from typing import Any

import pytest

from omnibase_core.models.core.model_yaml_list import ModelYamlList
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


class TestModelYamlList:
    """Test suite for ModelYamlList."""

    def test_initialization_empty(self):
        """Test initialization with no arguments."""
        model = ModelYamlList(version=DEFAULT_VERSION)

        assert model.root_list == []
        assert isinstance(model.root_list, list)

    def test_initialization_with_list(self):
        """Test initialization with list data."""
        data = ["item1", "item2", "item3"]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert len(model.root_list) == 3

    def test_initialization_with_dict_list(self):
        """Test initialization with list of dictionaries."""
        data = [
            {"key": "value1", "num": 1},
            {"key": "value2", "num": 2},
        ]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert len(model.root_list) == 2
        assert model.root_list[0]["key"] == "value1"

    def test_initialization_with_mixed_types(self):
        """Test initialization with mixed type list."""
        data = ["string", 123, {"key": "value"}, [1, 2, 3], None, True]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert len(model.root_list) == 6
        assert model.root_list[0] == "string"
        assert model.root_list[1] == 123
        assert model.root_list[2] == {"key": "value"}
        assert model.root_list[3] == [1, 2, 3]
        assert model.root_list[4] is None
        assert model.root_list[5] is True

    def test_initialization_with_none_data(self):
        """Test initialization with None data."""
        model = ModelYamlList(data=None)

        assert model.root_list == []

    def test_initialization_with_kwargs_only(self):
        """Test initialization with kwargs but no data."""
        model = ModelYamlList(root_list=["a", "b", "c"])

        assert model.root_list == ["a", "b", "c"]

    def test_initialization_data_and_kwargs(self):
        """Test that data parameter takes precedence over kwargs."""
        data = ["data1", "data2"]

        model = ModelYamlList(data=data, root_list=["ignored"])

        # data parameter should win
        assert model.root_list == data

    def test_initialization_with_nested_lists(self):
        """Test initialization with nested list structures."""
        data = [
            ["nested", "list", 1],
            ["another", "nested", 2],
            [[["deeply"], ["nested"]]],
        ]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert len(model.root_list) == 3
        assert model.root_list[0] == ["nested", "list", 1]
        assert model.root_list[2] == [[["deeply"], ["nested"]]]

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed (ConfigDict extra='allow')."""
        model = ModelYamlList(data=["item1"], extra_field="extra_value")

        assert model.root_list == ["item1"]
        assert model.extra_field == "extra_value"

    def test_model_dump(self):
        """Test model serialization."""
        data = ["item1", "item2"]
        model = ModelYamlList(data=data)

        dumped = model.model_dump()

        assert isinstance(dumped, dict)
        assert "root_list" in dumped
        assert dumped["root_list"] == data

    def test_model_dump_json(self):
        """Test JSON serialization."""
        data = ["item1", "item2", {"key": "value"}]
        model = ModelYamlList(data=data)

        json_str = model.model_dump_json()

        assert isinstance(json_str, str)
        assert "item1" in json_str
        assert "item2" in json_str

    def test_empty_list(self):
        """Test with empty list."""
        model = ModelYamlList(data=[])

        assert model.root_list == []
        assert len(model.root_list) == 0

    def test_single_item_list(self):
        """Test with single item list."""
        model = ModelYamlList(data=["single"])

        assert model.root_list == ["single"]
        assert len(model.root_list) == 1

    def test_large_list(self):
        """Test with large list."""
        data = list(range(1000))

        model = ModelYamlList(data=data)

        assert len(model.root_list) == 1000
        assert model.root_list[0] == 0
        assert model.root_list[999] == 999

    def test_list_with_none_values(self):
        """Test list containing None values."""
        data = ["value", None, "another", None]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert model.root_list[1] is None
        assert model.root_list[3] is None

    def test_list_modification(self):
        """Test that root_list can be modified."""
        model = ModelYamlList(data=["original"])

        model.root_list.append("new_item")

        assert len(model.root_list) == 2
        assert model.root_list[-1] == "new_item"

    def test_list_with_complex_objects(self):
        """Test list with complex nested objects."""
        data = [
            {
                "name": "item1",
                "nested": {"level2": {"level3": ["deep", "values"]}},
                "list": [1, 2, 3],
            },
            {"name": "item2", "values": [{"a": 1}, {"b": 2}]},
        ]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert model.root_list[0]["nested"]["level2"]["level3"] == ["deep", "values"]
        assert model.root_list[1]["values"][0]["a"] == 1


class TestModelYamlListEdgeCases:
    """Edge case tests for ModelYamlList."""

    def test_unicode_strings(self):
        """Test with unicode strings."""
        data = ["Hello 世界", "Привет", "مرحبا", "🎉🎊"]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert model.root_list[0] == "Hello 世界"
        assert model.root_list[3] == "🎉🎊"

    def test_special_characters(self):
        """Test with special characters."""
        data = [
            "line1\nline2",
            "tab\there",
            'quote"inside',
            "single'quote",
            "backslash\\here",
        ]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert "\n" in model.root_list[0]
        assert "\t" in model.root_list[1]

    def test_numeric_strings(self):
        """Test with numeric strings vs actual numbers."""
        data = ["123", 123, "45.67", 45.67]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert isinstance(model.root_list[0], str)
        assert isinstance(model.root_list[1], int)
        assert isinstance(model.root_list[2], str)
        assert isinstance(model.root_list[3], float)

    def test_boolean_values(self):
        """Test with boolean values."""
        data = [True, False, "true", "false", 1, 0]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert model.root_list[0] is True
        assert model.root_list[1] is False
        assert model.root_list[2] == "true"
        assert model.root_list[3] == "false"

    def test_very_long_strings(self):
        """Test with very long strings."""
        long_string = "x" * 10000
        data = [long_string]

        model = ModelYamlList(data=data)

        assert len(model.root_list[0]) == 10000
        assert model.root_list[0] == long_string

    def test_deeply_nested_structures(self):
        """Test with deeply nested structures."""
        data = [[[[[[["deep"]]]]]]]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        # Navigate to deepest level
        current = model.root_list
        for _ in range(6):
            current = current[0]
        assert current == ["deep"]

    def test_initialization_not_list(self):
        """Test initialization with non-list data."""
        # When data is not a list, should use default initialization
        model = ModelYamlList(data="not a list")

        # Should have empty list since data wasn't a list
        assert model.root_list == []

    def test_initialization_dict_data(self):
        """Test initialization with dict data (not a list)."""
        model = ModelYamlList(data={"key": "value"})

        # Should use default since data is not a list
        assert model.root_list == []

    def test_model_copy(self):
        """Test model copying."""
        original = ModelYamlList(data=["item1", "item2"])

        copy = original.model_copy()

        assert copy.root_list == original.root_list
        assert copy is not original

    def test_model_copy_deep(self):
        """Test deep model copying."""
        original = ModelYamlList(data=[{"nested": {"key": "value"}}])

        copy = original.model_copy(deep=True)

        # Modify copy
        copy.root_list[0]["nested"]["key"] = "modified"

        # Original should be unchanged
        assert original.root_list[0]["nested"]["key"] == "value"

    def test_model_validate(self):
        """Test model validation."""
        data = ["valid", "data"]

        # Should validate without error
        model = ModelYamlList.model_validate({"root_list": data})

        assert model.root_list == data

    def test_empty_dict_in_list(self):
        """Test with empty dict in list."""
        data = [{}, {"key": "value"}, {}]

        model = ModelYamlList(data=data)

        assert model.root_list == data
        assert model.root_list[0] == {}
        assert model.root_list[1] == {"key": "value"}
        assert model.root_list[2] == {}
