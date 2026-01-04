"""Tests for ModelOutputDiff model.

Tests the output diff model used for structured difference representation
between baseline and replay execution outputs.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.comparison import ModelOutputDiff, ModelValueChange


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

    IMPORTANT: has_differences is a computed field derived from content.
    It should NOT be passed to the constructor.
    """

    def test_has_differences_true_when_values_changed_not_empty(self) -> None:
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

    def test_has_differences_is_computed_not_stored(self) -> None:
        """has_differences is recomputed based on current state."""
        # Create empty diff
        diff = ModelOutputDiff()
        assert diff.has_differences is False

        # Create diff with data
        diff_with_data = ModelOutputDiff(
            items_added=["root['item']"],
        )
        assert diff_with_data.has_differences is True


@pytest.mark.unit
class TestModelOutputDiffImmutability:
    """Test immutability of ModelOutputDiff model."""

    def test_model_is_frozen_after_creation(self) -> None:
        """Model is immutable (frozen) after creation."""
        diff = ModelOutputDiff(
            items_added=["root['item']"],
        )
        with pytest.raises(ValidationError):
            diff.items_added = ["modified"]  # type: ignore[misc]
        with pytest.raises(ValidationError):
            diff.values_changed = {}  # type: ignore[misc]
        with pytest.raises(ValidationError):
            diff.type_changes = {}  # type: ignore[misc]

    def test_model_cannot_be_hashed_due_to_mutable_fields(self) -> None:
        """Frozen model with mutable fields (dict, list) cannot be hashed.

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

    def test_serialization_to_dict(self) -> None:
        """Model can be serialized to dictionary."""
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

    def test_serialization_empty_diff_to_dict(self) -> None:
        """Empty diff serializes with empty collections."""
        diff = ModelOutputDiff()
        data = diff.model_dump()
        assert data["values_changed"] == {}
        assert data["items_added"] == []
        assert data["items_removed"] == []
        assert data["type_changes"] == {}
        assert data["has_differences"] is False

    def test_serialization_to_json(self) -> None:
        """Model can be serialized to JSON string."""
        diff = ModelOutputDiff(
            items_added=["root['new_item']"],
        )
        json_str = diff.model_dump_json()
        assert isinstance(json_str, str)
        assert '"items_added":["root[\'new_item\']"]' in json_str
        assert '"has_differences":true' in json_str

    def test_deserialization_from_dict(self) -> None:
        """Model can be created from dictionary data."""
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

    def test_model_validate_from_object_attributes(self) -> None:
        """Model can be created from object attributes via model_validate."""

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

    def test_handles_deepdiff_json_path_format(self) -> None:
        """Model handles deepdiff JSON path format for keys."""
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

    def test_handles_nested_value_changes(self) -> None:
        """Model handles multiple nested value changes."""
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

    def test_handles_empty_string_paths(self) -> None:
        """Model handles empty string as path key."""
        diff = ModelOutputDiff(
            items_added=[""],
        )
        assert "" in diff.items_added

    def test_handles_many_changes(self) -> None:
        """Model handles large number of changes."""
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

    def test_handles_complex_type_change_descriptions(self) -> None:
        """Model handles complex type change descriptions."""
        diff = ModelOutputDiff(
            type_changes={
                "root['key']": "NoneType -> dict[str, Any]",
                "root['list']": "list[int] -> list[str]",
            },
        )
        assert len(diff.type_changes) == 2

    def test_extra_fields_are_ignored(self) -> None:
        """Extra fields in input are ignored (ConfigDict extra='ignore')."""
        data: dict[str, Any] = {
            "values_changed": {},
            "items_added": [],
            "items_removed": [],
            "type_changes": {},
            "extra_field": "should be ignored",
        }
        diff = ModelOutputDiff(**data)
        assert not hasattr(diff, "extra_field")

    def test_handles_special_characters_in_paths(self) -> None:
        """Model handles special characters in path strings."""
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
