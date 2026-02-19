# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelOutputDiff model.

Tests the output diff model used for structured difference representation
between baseline and replay execution outputs.
"""

from typing import Any

import pytest
from deepdiff import DeepDiff
from pydantic import ValidationError

from omnibase_core.models.replay import ModelOutputDiff, ModelValueChange


@pytest.mark.unit
class TestModelOutputDiffCreation:
    """Test ModelOutputDiff creation and initialization."""

    def test_creation_with_default_values_succeeds(self) -> None:
        """Model can be created with default (empty) values."""
        diff = ModelOutputDiff()
        assert diff.values_changed == {}
        assert diff.items_added == []
        assert diff.items_removed == []
        assert diff.type_changes == {}

    def test_creation_with_all_fields_succeeds(self) -> None:
        """Model can be created with all fields populated."""
        value_change = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        diff = ModelOutputDiff(
            values_changed={"root['key']": value_change},
            items_added=["root['new_key']"],
            items_removed=["root['old_key']"],
            type_changes={"root['type_key']": "int -> str"},
        )
        assert len(diff.values_changed) == 1
        assert "root['key']" in diff.values_changed
        assert diff.values_changed["root['key']"] == value_change
        assert diff.items_added == ["root['new_key']"]
        assert diff.items_removed == ["root['old_key']"]
        assert diff.type_changes["root['type_key']"] == "int -> str"

    def test_creation_with_partial_fields_succeeds(self) -> None:
        """Model can be created with only some fields populated."""
        diff = ModelOutputDiff(
            items_added=["root['new_item']"],
        )
        assert diff.values_changed == {}
        assert diff.items_added == ["root['new_item']"]
        assert diff.items_removed == []
        assert diff.type_changes == {}


@pytest.mark.unit
class TestModelOutputDiffComputedField:
    """Test has_differences computed field behavior.

    IMPORTANT - Computed Field Behavior:
        - ``has_differences`` is a @computed_field, NOT a stored field
        - It is derived from checking if ANY of (values_changed, items_added,
          items_removed, type_changes) contains data
        - It cannot be overridden via constructor (extra="ignore" silently ignores it)
        - The value is always dynamically computed from actual content

    This test class verifies all computed field behaviors for has_differences.
    """

    def test_computed_has_differences_returns_true_when_values_changed_not_empty(
        self,
    ) -> None:
        """has_differences is True when values_changed has entries."""
        diff = ModelOutputDiff(
            values_changed={
                "root['key']": ModelValueChange(
                    old_value="old",
                    new_value="new",
                )
            },
        )
        assert diff.has_differences is True

    def test_has_differences_true_when_items_added_not_empty(self) -> None:
        """has_differences is True when items_added has entries."""
        diff = ModelOutputDiff(
            items_added=["root['new_item']"],
        )
        assert diff.has_differences is True

    def test_has_differences_true_when_items_removed_not_empty(self) -> None:
        """has_differences is True when items_removed has entries."""
        diff = ModelOutputDiff(
            items_removed=["root['old_item']"],
        )
        assert diff.has_differences is True

    def test_has_differences_true_when_type_changes_not_empty(self) -> None:
        """has_differences is True when type_changes has entries."""
        diff = ModelOutputDiff(
            type_changes={"root['key']": "int -> str"},
        )
        assert diff.has_differences is True

    def test_has_differences_false_when_all_collections_empty(self) -> None:
        """has_differences is False when all collections are empty."""
        diff = ModelOutputDiff()
        assert diff.has_differences is False

    def test_has_differences_true_when_multiple_collections_populated(self) -> None:
        """has_differences is True when multiple collections have data."""
        diff = ModelOutputDiff(
            values_changed={
                "root['key']": ModelValueChange(
                    old_value="old",
                    new_value="new",
                )
            },
            items_added=["root['added']"],
            items_removed=["root['removed']"],
            type_changes={"root['type']": "str -> int"},
        )
        assert diff.has_differences is True

    def test_computed_has_differences_is_derived_not_stored(self) -> None:
        """Computed field has_differences is derived dynamically, not stored."""
        # Create empty diff
        diff = ModelOutputDiff()
        assert diff.has_differences is False

        # Create diff with data
        diff_with_data = ModelOutputDiff(
            items_added=["root['item']"],
        )
        assert diff_with_data.has_differences is True

    def test_computed_has_differences_ignores_constructor_param(self) -> None:
        """Computed field has_differences ignores constructor parameter attempts.

        IMPORTANT - Computed Field Behavior:
            - ``has_differences`` is a @computed_field, NOT a stored field
            - Any attempt to pass it to the constructor is silently ignored
              (due to ConfigDict extra='ignore')
            - The computed value is always derived from actual content fields
        """
        # Attempt to force has_differences=False when there ARE actual differences
        # The computed_field decorator ensures the value is derived from content
        diff_with_differences = ModelOutputDiff(
            items_added=["root['new_item']"],
            has_differences=False,  # type: ignore[call-arg]  # Intentionally passing invalid param
        )
        # Computed field should return True based on items_added content
        assert diff_with_differences.has_differences is True

        # Attempt to force has_differences=True when there are NO actual differences
        diff_without_differences = ModelOutputDiff(
            has_differences=True,  # type: ignore[call-arg]  # Intentionally passing invalid param
        )
        # Computed field should return False based on empty content
        assert diff_without_differences.has_differences is False


@pytest.mark.unit
class TestModelOutputDiffImmutability:
    """Test immutability of ModelOutputDiff model."""

    def test_mutation_on_frozen_model_raises_validation_error(self) -> None:
        """Mutation attempt on frozen model raises ValidationError."""
        diff = ModelOutputDiff(
            items_added=["root['item']"],
        )
        with pytest.raises(ValidationError):
            diff.items_added = ["modified"]  # type: ignore[misc]
        with pytest.raises(ValidationError):
            diff.values_changed = {}  # type: ignore[misc]
        with pytest.raises(ValidationError):
            diff.type_changes = {}  # type: ignore[misc]

    def test_hashing_model_with_mutable_fields_raises_type_error(self) -> None:
        """Hashing model with mutable fields raises TypeError.

        While the model is frozen (immutable at model level), the underlying
        dict and list fields are mutable types which prevent hashing.
        This is expected Pydantic behavior for frozen models with mutable field types.
        """
        diff = ModelOutputDiff(
            items_added=["root['item']"],
        )
        with pytest.raises(TypeError, match="unhashable type"):
            hash(diff)


@pytest.mark.unit
class TestModelOutputDiffSerialization:
    """Test serialization of ModelOutputDiff model."""

    def test_serialization_to_dict_succeeds(self) -> None:
        """Serialization to dictionary returns complete dict with computed field."""
        value_change = ModelValueChange(
            old_value="original",
            new_value="updated",
        )
        diff = ModelOutputDiff(
            values_changed={"root['key']": value_change},
            items_added=["root['added']"],
            items_removed=["root['removed']"],
            type_changes={"root['type']": "int -> str"},
        )
        data = diff.model_dump()
        assert isinstance(data, dict)
        assert "values_changed" in data
        assert "items_added" in data
        assert "items_removed" in data
        assert "type_changes" in data
        assert "has_differences" in data  # Computed field included
        assert data["has_differences"] is True

    def test_serialization_empty_diff_to_dict_succeeds(self) -> None:
        """Serialization of empty diff returns dict with empty collections."""
        diff = ModelOutputDiff()
        data = diff.model_dump()
        assert data["values_changed"] == {}
        assert data["items_added"] == []
        assert data["items_removed"] == []
        assert data["type_changes"] == {}
        assert data["has_differences"] is False

    def test_serialization_to_json_succeeds(self) -> None:
        """Serialization to JSON returns valid string representation."""
        diff = ModelOutputDiff(
            items_added=["root['new_item']"],
        )
        json_str = diff.model_dump_json()
        assert isinstance(json_str, str)
        assert '"items_added":["root[\'new_item\']"]' in json_str
        assert '"has_differences":true' in json_str

    def test_deserialization_from_dict_succeeds(self) -> None:
        """Deserialization from dictionary creates valid model."""
        data: dict[str, Any] = {
            "values_changed": {
                "root['key']": {
                    "old_value": "old",
                    "new_value": "new",
                }
            },
            "items_added": ["root['added']"],
            "items_removed": [],
            "type_changes": {},
        }
        diff = ModelOutputDiff(**data)
        assert len(diff.values_changed) == 1
        assert diff.values_changed["root['key']"].old_value == "old"
        assert diff.items_added == ["root['added']"]
        assert diff.has_differences is True

    def test_model_validate_from_attributes_succeeds(self) -> None:
        """Model validation from object attributes creates valid model."""

        class DiffData:
            """Mock object with diff attributes."""

            def __init__(self) -> None:
                self.values_changed: dict[str, ModelValueChange] = {}
                self.items_added = ["root['item']"]
                self.items_removed: list[str] = []
                self.type_changes: dict[str, str] = {}

        diff = ModelOutputDiff.model_validate(DiffData())
        assert diff.items_added == ["root['item']"]
        assert diff.has_differences is True


@pytest.mark.unit
class TestModelOutputDiffDeepDiffCompatibility:
    """Test compatibility with deepdiff library output format."""

    def test_creation_with_deepdiff_json_path_format_succeeds(self) -> None:
        """Creation with deepdiff JSON path format for keys succeeds."""
        diff = ModelOutputDiff(
            values_changed={
                "root['response']['data'][0]['value']": ModelValueChange(
                    old_value="42",
                    new_value="100",
                )
            },
            items_added=["root['response']['metadata']['new_field']"],
            items_removed=["root['response']['deprecated_field']"],
            type_changes={"root['count']": "int -> str"},
        )
        assert "root['response']['data'][0]['value']" in diff.values_changed
        assert "root['response']['metadata']['new_field']" in diff.items_added
        assert "root['response']['deprecated_field']" in diff.items_removed
        assert "root['count']" in diff.type_changes

    def test_creation_with_nested_value_changes_succeeds(self) -> None:
        """Creation with multiple nested value changes succeeds."""
        diff = ModelOutputDiff(
            values_changed={
                "root['a']": ModelValueChange(old_value="1", new_value="2"),
                "root['b']['c']": ModelValueChange(old_value="x", new_value="y"),
                "root['d'][0]": ModelValueChange(old_value="old", new_value="new"),
            },
        )
        assert len(diff.values_changed) == 3
        assert diff.has_differences is True


@pytest.mark.unit
class TestModelOutputDiffEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_creation_with_empty_string_paths_succeeds(self) -> None:
        """Creation with empty string as path key succeeds."""
        diff = ModelOutputDiff(
            items_added=[""],
        )
        assert "" in diff.items_added

    def test_creation_with_many_changes_succeeds(self) -> None:
        """Creation with large number of changes succeeds."""
        many_changes = {
            f"root['key_{i}']": ModelValueChange(
                old_value=f"old_{i}",
                new_value=f"new_{i}",
            )
            for i in range(100)
        }
        diff = ModelOutputDiff(values_changed=many_changes)
        assert len(diff.values_changed) == 100
        assert diff.has_differences is True

    def test_creation_with_complex_type_changes_succeeds(self) -> None:
        """Creation with complex type change descriptions succeeds."""
        diff = ModelOutputDiff(
            type_changes={
                "root['key']": "NoneType -> dict[str, Any]",
                "root['list']": "list[int] -> list[str]",
            },
        )
        assert len(diff.type_changes) == 2

    def test_creation_with_extra_fields_ignores_them(self) -> None:
        """Creation with extra fields ignores them (ConfigDict extra='ignore')."""
        data: dict[str, Any] = {
            "values_changed": {},
            "items_added": [],
            "items_removed": [],
            "type_changes": {},
            "extra_field": "should be ignored",
        }
        diff = ModelOutputDiff(**data)
        assert not hasattr(diff, "extra_field")

    def test_creation_with_special_characters_in_paths_succeeds(self) -> None:
        """Creation with special characters in path strings succeeds."""
        diff = ModelOutputDiff(
            items_added=[
                "root['key with spaces']",
                "root['key-with-dashes']",
                "root['key.with.dots']",
                "root['key:with:colons']",
            ],
        )
        assert len(diff.items_added) == 4


@pytest.mark.unit
class TestModelOutputDiffEquality:
    """Test equality and comparison behavior."""

    def test_equality_when_same_values_returns_true(self) -> None:
        """Two instances with identical values are equal."""
        change = ModelValueChange(old_value="old", new_value="new")
        diff1 = ModelOutputDiff(
            values_changed={"root['key']": change},
            items_added=["root['added']"],
        )
        diff2 = ModelOutputDiff(
            values_changed={"root['key']": change},
            items_added=["root['added']"],
        )
        assert diff1 == diff2

    def test_equality_when_different_values_changed_returns_false(self) -> None:
        """Two instances with different values_changed are not equal."""
        diff1 = ModelOutputDiff(
            values_changed={
                "root['key']": ModelValueChange(
                    old_value="old1",
                    new_value="new1",
                )
            },
        )
        diff2 = ModelOutputDiff(
            values_changed={
                "root['key']": ModelValueChange(
                    old_value="old2",
                    new_value="new2",
                )
            },
        )
        assert diff1 != diff2

    def test_equality_empty_diffs_are_equal(self) -> None:
        """Two empty diffs are equal."""
        diff1 = ModelOutputDiff()
        diff2 = ModelOutputDiff()
        assert diff1 == diff2


@pytest.mark.unit
class TestModelOutputDiffWithFixture:
    """Test using fixtures from conftest.py."""

    def test_creation_from_fixture_succeeds(
        self, sample_output_diff: ModelOutputDiff
    ) -> None:
        """Model can be created and accessed via fixture."""
        assert isinstance(sample_output_diff, ModelOutputDiff)
        assert sample_output_diff.has_differences is True
        assert len(sample_output_diff.values_changed) == 1

    def test_fixture_contains_expected_value_change(
        self, sample_output_diff: ModelOutputDiff
    ) -> None:
        """Fixture contains expected value change data."""
        assert "root['response']['text']" in sample_output_diff.values_changed
        change = sample_output_diff.values_changed["root['response']['text']"]
        assert change.old_value == "Original response"
        assert change.new_value == "Updated response"


@pytest.mark.unit
class TestModelOutputDiffFromDeepDiff:
    """Test from_deepdiff factory method for converting deepdiff output."""

    def test_from_deepdiff_basic_values_changed_succeeds(self) -> None:
        """Factory converts basic values_changed from deepdiff."""
        baseline = {"key": "old_value"}
        replay = {"key": "new_value"}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert len(output_diff.values_changed) == 1
        assert "root['key']" in output_diff.values_changed
        change = output_diff.values_changed["root['key']"]
        assert change.old_value == "old_value"
        assert change.new_value == "new_value"

    def test_from_deepdiff_empty_diff_returns_no_differences(self) -> None:
        """Factory handles empty diff (identical objects)."""
        baseline = {"key": "value"}
        replay = {"key": "value"}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is False
        assert output_diff.values_changed == {}
        assert output_diff.items_added == []
        assert output_diff.items_removed == []
        assert output_diff.type_changes == {}

    def test_from_deepdiff_dictionary_items_added_succeeds(self) -> None:
        """Factory handles dictionary items added."""
        baseline = {"existing": 1}
        replay = {"existing": 1, "new_key": 2}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert "root['new_key']" in output_diff.items_added

    def test_from_deepdiff_dictionary_items_removed_succeeds(self) -> None:
        """Factory handles dictionary items removed."""
        baseline = {"existing": 1, "removed_key": 2}
        replay = {"existing": 1}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert "root['removed_key']" in output_diff.items_removed

    def test_from_deepdiff_iterable_items_added_succeeds(self) -> None:
        """Factory handles iterable items added."""
        baseline = [1, 2]
        replay = [1, 2, 3]
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert "root[2]" in output_diff.items_added

    def test_from_deepdiff_iterable_items_removed_succeeds(self) -> None:
        """Factory handles iterable items removed."""
        baseline = [1, 2, 3]
        replay = [1, 2]
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert "root[2]" in output_diff.items_removed

    def test_from_deepdiff_type_changes_succeeds(self) -> None:
        """Factory handles type changes."""
        baseline = {"key": 42}
        replay = {"key": "42"}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert "root['key']" in output_diff.type_changes
        type_change = output_diff.type_changes["root['key']"]
        assert "int" in type_change
        assert "str" in type_change
        assert "->" in type_change

    def test_from_deepdiff_multiple_categories_succeeds(self) -> None:
        """Factory handles diff with multiple change categories."""
        baseline = {"changed": "old", "removed": 1, "typed": 100}
        replay = {"changed": "new", "added": 2, "typed": "100"}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # Check values_changed
        assert "root['changed']" in output_diff.values_changed
        # Check items_added
        assert "root['added']" in output_diff.items_added
        # Check items_removed
        assert "root['removed']" in output_diff.items_removed
        # Check type_changes
        assert "root['typed']" in output_diff.type_changes

    def test_from_deepdiff_nested_structure_succeeds(self) -> None:
        """Factory handles nested data structures."""
        baseline = {"outer": {"inner": {"deep": "old_value"}}}
        replay = {"outer": {"inner": {"deep": "new_value"}}}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert len(output_diff.values_changed) == 1
        # Check path contains nested structure
        path = next(iter(output_diff.values_changed.keys()))
        assert "outer" in path
        assert "inner" in path
        assert "deep" in path

    def test_from_deepdiff_various_value_types_succeeds(self) -> None:
        """Factory handles various Python value types."""
        baseline = {
            "int_val": 42,
            "float_val": 3.14,
            "bool_val": True,
            "list_val": [1, 2],
            "none_val": None,
        }
        replay = {
            "int_val": 100,
            "float_val": 2.71,
            "bool_val": False,
            "list_val": [3, 4],
            "none_val": "not_none",
        }
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # Verify numeric values are serialized
        if "root['int_val']" in output_diff.values_changed:
            change = output_diff.values_changed["root['int_val']"]
            assert change.old_value == "42"
            assert change.new_value == "100"
        # Verify float values
        if "root['float_val']" in output_diff.values_changed:
            change = output_diff.values_changed["root['float_val']"]
            assert "3.14" in change.old_value
            assert "2.71" in change.new_value

    def test_from_deepdiff_with_dict_input_succeeds(self) -> None:
        """Factory handles raw dictionary input (not DeepDiff object)."""
        raw_diff: dict[str, Any] = {
            "values_changed": {"root['key']": {"old_value": "old", "new_value": "new"}},
            "dictionary_item_added": {"root['added']": "value"},
        }

        output_diff = ModelOutputDiff.from_deepdiff(raw_diff)

        assert output_diff.has_differences is True
        assert "root['key']" in output_diff.values_changed
        assert "root['added']" in output_diff.items_added

    def test_from_deepdiff_with_only_values_changed_succeeds(self) -> None:
        """Factory handles diff with only values_changed populated."""
        baseline = {"a": 1, "b": 2}
        replay = {"a": 10, "b": 20}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert len(output_diff.values_changed) == 2
        assert output_diff.items_added == []
        assert output_diff.items_removed == []
        assert output_diff.type_changes == {}

    def test_from_deepdiff_with_only_type_changes_succeeds(self) -> None:
        """Factory handles diff with only type_changes populated."""
        baseline = {"key": 42}
        replay = {"key": "42"}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert len(output_diff.type_changes) == 1
        # values_changed may or may not be populated depending on deepdiff version
        assert output_diff.items_added == []
        assert output_diff.items_removed == []

    def test_from_deepdiff_with_empty_dict_input_succeeds(self) -> None:
        """Factory handles empty dictionary input."""
        output_diff = ModelOutputDiff.from_deepdiff({})

        assert output_diff.has_differences is False
        assert output_diff.values_changed == {}
        assert output_diff.items_added == []
        assert output_diff.items_removed == []
        assert output_diff.type_changes == {}

    def test_from_deepdiff_serializes_complex_values(self) -> None:
        """Factory serializes complex values to string representation."""
        baseline = {"key": {"nested": [1, 2, 3]}}
        replay = {"key": {"nested": [4, 5, 6]}}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        # Depending on deepdiff behavior, this may show in values_changed
        # or iterable changes. The key test is that it converts without error.
        assert isinstance(output_diff, ModelOutputDiff)

    def test_from_deepdiff_type_change_format_is_readable(self) -> None:
        """Type change descriptions follow 'old_type -> new_type' format."""
        baseline = {"val": 123}
        replay = {"val": [1, 2, 3]}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        if output_diff.type_changes:
            type_change = next(iter(output_diff.type_changes.values()))
            assert "->" in type_change
            parts = type_change.split("->")
            assert len(parts) == 2
            assert parts[0].strip()  # Non-empty old type
            assert parts[1].strip()  # Non-empty new type

    def test_from_deepdiff_deeply_nested_structure_four_levels_succeeds(self) -> None:
        """Factory handles deeply nested structures (4+ levels deep)."""
        baseline = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": "old_deep_value",
                        },
                    },
                },
            },
        }
        replay = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": "new_deep_value",
                        },
                    },
                },
            },
        }
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert len(output_diff.values_changed) == 1
        path = next(iter(output_diff.values_changed.keys()))
        # Verify path contains all nesting levels
        assert "level1" in path
        assert "level2" in path
        assert "level3" in path
        assert "level4" in path
        assert "level5" in path
        change = output_diff.values_changed[path]
        assert change.old_value == "old_deep_value"
        assert change.new_value == "new_deep_value"

    def test_from_deepdiff_mixed_list_and_dict_nesting_succeeds(self) -> None:
        """Factory handles mixed list and dict nesting patterns."""
        baseline = {"a": [{"b": {"c": [1, 2, 3]}}]}
        replay = {"a": [{"b": {"c": [4, 5, 6]}}]}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # The diff should capture the changes in the nested list
        assert isinstance(output_diff, ModelOutputDiff)
        # Verify conversion succeeded without errors
        total_changes = (
            len(output_diff.values_changed)
            + len(output_diff.items_added)
            + len(output_diff.items_removed)
            + len(output_diff.type_changes)
        )
        assert total_changes > 0

    def test_from_deepdiff_very_large_numeric_changes_succeeds(self) -> None:
        """Factory handles very large percentage changes in numeric values."""
        baseline = {
            "tiny_to_huge": 0.0000001,
            "huge_to_tiny": 999999999999,
            "negative_to_positive": -1000000,
            "zero_to_large": 0,
        }
        replay = {
            "tiny_to_huge": 999999999999,
            "huge_to_tiny": 0.0000001,
            "negative_to_positive": 1000000,
            "zero_to_large": float("inf"),
        }
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # DeepDiff categorizes float<->int conversions as type_changes
        # Only same-type value changes go into values_changed
        total_changes = len(output_diff.values_changed) + len(output_diff.type_changes)
        assert total_changes >= 4
        # Verify type changes are captured for float/int conversions
        assert len(output_diff.type_changes) >= 1
        # Check that negative_to_positive (int -> int) is in values_changed
        assert "root['negative_to_positive']" in output_diff.values_changed
        change = output_diff.values_changed["root['negative_to_positive']"]
        assert change.old_value == "-1000000"
        assert change.new_value == "1000000"

    def test_from_deepdiff_unicode_special_characters_in_keys_succeeds(self) -> None:
        """Factory handles unicode and special characters in dictionary keys."""
        baseline = {
            "emoji_key_🔑": "old_value",
            "日本語キー": "japanese_old",
            "clé_française": "french_old",
            "ключ_русский": "russian_old",
            "key\nwith\nnewlines": "newline_old",
            "key\twith\ttabs": "tab_old",
        }
        replay = {
            "emoji_key_🔑": "new_value",
            "日本語キー": "japanese_new",
            "clé_française": "french_new",
            "ключ_русский": "russian_new",
            "key\nwith\nnewlines": "newline_new",
            "key\twith\ttabs": "tab_new",
        }
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert len(output_diff.values_changed) == 6
        # Verify all keys are properly converted
        for change in output_diff.values_changed.values():
            assert (
                change.old_value.endswith("_old") or "old" in change.old_value.lower()
            )
            assert (
                change.new_value.endswith("_new") or "new" in change.new_value.lower()
            )

    def test_from_deepdiff_unicode_special_characters_in_values_succeeds(self) -> None:
        """Factory handles unicode and special characters in values."""
        baseline = {
            "emoji": "👍 thumbs up",
            "chinese": "中文文本",
            "arabic": "النص العربي",
            "special": "line1\nline2\ttabbed",
            "quotes": 'single\' and "double"',
        }
        replay = {
            "emoji": "👎 thumbs down",
            "chinese": "更新的中文",
            "arabic": "تحديث النص",
            "special": "updated\nlines\there",
            "quotes": 'updated\' and "quotes"',
        }
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        assert len(output_diff.values_changed) == 5
        # Check emoji key specifically
        emoji_path = "root['emoji']"
        if emoji_path in output_diff.values_changed:
            change = output_diff.values_changed[emoji_path]
            assert "👍" in change.old_value
            assert "👎" in change.new_value

    def test_from_deepdiff_empty_nested_dicts_succeeds(self) -> None:
        """Factory handles empty nested dictionaries."""
        baseline = {"outer": {"empty_dict": {}}}
        replay = {"outer": {"empty_dict": {"now_has": "value"}}}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # Item was added to the previously empty dict
        assert len(output_diff.items_added) >= 1

    def test_from_deepdiff_empty_nested_lists_succeeds(self) -> None:
        """Factory handles empty nested lists."""
        baseline = {"data": {"items": []}}
        replay = {"data": {"items": [1, 2, 3]}}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # Items were added to the previously empty list
        assert len(output_diff.items_added) >= 1

    def test_from_deepdiff_nested_becoming_empty_succeeds(self) -> None:
        """Factory handles nested structures becoming empty."""
        baseline = {"data": {"items": [1, 2, 3], "mapping": {"a": 1}}}
        replay = {"data": {"items": [], "mapping": {}}}
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # Items were removed from both the list and dict
        assert len(output_diff.items_removed) >= 1

    def test_from_deepdiff_with_ignore_order_true_succeeds(self) -> None:
        """Factory handles DeepDiff with ignore_order=True parameter."""
        baseline = {"items": [1, 2, 3]}
        replay = {"items": [3, 2, 1]}  # Same items, different order
        diff = DeepDiff(baseline, replay, ignore_order=True)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        # With ignore_order=True, reordered lists should show no differences
        assert output_diff.has_differences is False
        assert output_diff.values_changed == {}
        assert output_diff.items_added == []
        assert output_diff.items_removed == []

    def test_from_deepdiff_with_ignore_order_detects_value_changes(self) -> None:
        """Factory with ignore_order=True still detects actual value changes."""
        baseline = {"items": [1, 2, 3]}
        replay = {"items": [3, 2, 4]}  # 1 changed to 4, reordered
        diff = DeepDiff(baseline, replay, ignore_order=True)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        # Should detect that items changed even with ignore_order
        assert output_diff.has_differences is True
        total_changes = (
            len(output_diff.values_changed)
            + len(output_diff.items_added)
            + len(output_diff.items_removed)
        )
        assert total_changes >= 1

    def test_from_deepdiff_with_ignore_order_nested_dicts_in_lists(self) -> None:
        """Factory handles ignore_order with nested dicts in lists."""
        baseline = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
        replay = {"users": [{"id": 2, "name": "Bob"}, {"id": 1, "name": "Alice"}]}
        diff = DeepDiff(baseline, replay, ignore_order=True)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        # Reordering identical dicts should show no differences
        assert output_diff.has_differences is False

    def test_from_deepdiff_complex_mixed_changes_succeeds(self) -> None:
        """Factory handles complex structures with multiple change types."""
        baseline = {
            "metadata": {"version": 1, "tags": ["old"]},
            "data": [
                {"id": 1, "nested": {"deep": {"value": 100}}},
                {"id": 2, "nested": {"deep": {"value": 200}}},
            ],
            "config": {"enabled": True, "threshold": 0.5},
        }
        replay = {
            "metadata": {"version": 2, "tags": ["new", "updated"]},
            "data": [
                {"id": 1, "nested": {"deep": {"value": 150}}},
                {"id": 3, "nested": {"deep": {"value": 300}}},  # id changed
            ],
            "config": {"enabled": "yes", "threshold": 0.8},  # type change on enabled
        }
        diff = DeepDiff(baseline, replay)

        output_diff = ModelOutputDiff.from_deepdiff(diff)

        assert output_diff.has_differences is True
        # Verify multiple categories of changes are captured
        assert isinstance(output_diff.values_changed, dict)
        assert isinstance(output_diff.type_changes, dict)
        # Type change for enabled: bool -> str
        if output_diff.type_changes:
            type_change_found = any(
                "enabled" in path for path in output_diff.type_changes
            )
            assert type_change_found
