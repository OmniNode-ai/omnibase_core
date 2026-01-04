# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelContractFieldDiff."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff.model_contract_field_diff import (
    ModelContractFieldDiff,
)


@pytest.mark.unit
class TestModelContractFieldDiff:
    """Test suite for ModelContractFieldDiff model."""

    def test_added_change_requires_new_value(self) -> None:
        """Test ADDED requires new_value, not old_value."""
        diff = ModelContractFieldDiff(
            field_path="meta.name",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value("NewValue"),
            value_type="str",
        )
        assert diff.new_value is not None
        assert diff.old_value is None
        assert diff.change_type == EnumContractDiffChangeType.ADDED

    def test_added_change_rejects_old_value(self) -> None:
        """Test ADDED with old_value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.ADDED,
                old_value=ModelSchemaValue.from_value("OldValue"),
                new_value=ModelSchemaValue.from_value("NewValue"),
                value_type="str",
            )
        assert "ADDED change type must not have old_value" in str(exc_info.value)

    def test_added_change_rejects_missing_new_value(self) -> None:
        """Test ADDED without new_value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.ADDED,
                value_type="str",
            )
        assert "ADDED change type requires new_value" in str(exc_info.value)

    def test_removed_change_requires_old_value(self) -> None:
        """Test REMOVED requires old_value, not new_value."""
        diff = ModelContractFieldDiff(
            field_path="meta.name",
            change_type=EnumContractDiffChangeType.REMOVED,
            old_value=ModelSchemaValue.from_value("OldValue"),
            value_type="str",
        )
        assert diff.old_value is not None
        assert diff.new_value is None
        assert diff.change_type == EnumContractDiffChangeType.REMOVED

    def test_removed_change_rejects_new_value(self) -> None:
        """Test REMOVED with new_value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.REMOVED,
                old_value=ModelSchemaValue.from_value("OldValue"),
                new_value=ModelSchemaValue.from_value("NewValue"),
                value_type="str",
            )
        assert "REMOVED change type must not have new_value" in str(exc_info.value)

    def test_removed_change_rejects_missing_old_value(self) -> None:
        """Test REMOVED without old_value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.REMOVED,
                value_type="str",
            )
        assert "REMOVED change type requires old_value" in str(exc_info.value)

    def test_modified_requires_both_values(self) -> None:
        """Test MODIFIED requires both old and new values."""
        diff = ModelContractFieldDiff(
            field_path="meta.version",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value("1.0.0"),
            new_value=ModelSchemaValue.from_value("2.0.0"),
            value_type="str",
        )
        assert diff.old_value is not None
        assert diff.new_value is not None
        assert diff.change_type == EnumContractDiffChangeType.MODIFIED

    def test_modified_missing_old_raises(self) -> None:
        """Test MODIFIED without old_value raises."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="meta.version",
                change_type=EnumContractDiffChangeType.MODIFIED,
                new_value=ModelSchemaValue.from_value("2.0.0"),
                value_type="str",
            )
        assert "MODIFIED change type requires old_value" in str(exc_info.value)

    def test_modified_missing_new_raises(self) -> None:
        """Test MODIFIED without new_value raises."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="meta.version",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=ModelSchemaValue.from_value("1.0.0"),
                value_type="str",
            )
        assert "MODIFIED change type requires new_value" in str(exc_info.value)

    def test_moved_requires_indices(self) -> None:
        """Test MOVED requires both indices."""
        diff = ModelContractFieldDiff(
            field_path="transitions[0]",
            change_type=EnumContractDiffChangeType.MOVED,
            old_index=0,
            new_index=2,
            value_type="dict",
        )
        assert diff.old_index == 0
        assert diff.new_index == 2
        assert diff.change_type == EnumContractDiffChangeType.MOVED

    def test_moved_missing_old_index_raises(self) -> None:
        """Test MOVED without old_index raises."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="transitions[0]",
                change_type=EnumContractDiffChangeType.MOVED,
                new_index=2,
                value_type="dict",
            )
        assert "MOVED change type requires old_index" in str(exc_info.value)

    def test_moved_missing_new_index_raises(self) -> None:
        """Test MOVED without new_index raises."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="transitions[0]",
                change_type=EnumContractDiffChangeType.MOVED,
                old_index=0,
                value_type="dict",
            )
        assert "MOVED change type requires new_index" in str(exc_info.value)

    def test_unchanged_requires_both_values(self) -> None:
        """Test UNCHANGED requires both old_value and new_value."""
        value = ModelSchemaValue.from_value("SameValue")
        diff = ModelContractFieldDiff(
            field_path="meta.name",
            change_type=EnumContractDiffChangeType.UNCHANGED,
            old_value=value,
            new_value=value,
            value_type="str",
        )
        assert diff.old_value is not None
        assert diff.new_value is not None
        assert diff.change_type == EnumContractDiffChangeType.UNCHANGED

    def test_unchanged_missing_values_raises(self) -> None:
        """Test UNCHANGED without both values raises."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.UNCHANGED,
                value_type="str",
            )
        assert "UNCHANGED change type requires both old_value and new_value" in str(
            exc_info.value
        )

    def test_to_reverse_added_becomes_removed(self) -> None:
        """Test to_reverse() swaps ADDED to REMOVED."""
        original = ModelContractFieldDiff(
            field_path="meta.new_field",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value("NewValue"),
            value_type="str",
        )
        reversed_diff = original.to_reverse()
        assert reversed_diff.change_type == EnumContractDiffChangeType.REMOVED
        assert reversed_diff.old_value is not None
        assert reversed_diff.new_value is None

    def test_to_reverse_removed_becomes_added(self) -> None:
        """Test to_reverse() swaps REMOVED to ADDED."""
        original = ModelContractFieldDiff(
            field_path="meta.old_field",
            change_type=EnumContractDiffChangeType.REMOVED,
            old_value=ModelSchemaValue.from_value("OldValue"),
            value_type="str",
        )
        reversed_diff = original.to_reverse()
        assert reversed_diff.change_type == EnumContractDiffChangeType.ADDED
        assert reversed_diff.new_value is not None
        assert reversed_diff.old_value is None

    def test_to_reverse_swaps_values(self) -> None:
        """Test to_reverse() swaps old/new values."""
        original = ModelContractFieldDiff(
            field_path="meta.version",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value("1.0.0"),
            new_value=ModelSchemaValue.from_value("2.0.0"),
            value_type="str",
        )
        reversed_diff = original.to_reverse()
        assert reversed_diff.old_value is not None
        assert reversed_diff.new_value is not None
        assert reversed_diff.old_value.to_value() == "2.0.0"
        assert reversed_diff.new_value.to_value() == "1.0.0"

    def test_to_reverse_swaps_indices(self) -> None:
        """Test to_reverse() swaps old/new indices for MOVED."""
        original = ModelContractFieldDiff(
            field_path="transitions[0]",
            change_type=EnumContractDiffChangeType.MOVED,
            old_index=0,
            new_index=5,
            value_type="dict",
        )
        reversed_diff = original.to_reverse()
        assert reversed_diff.old_index == 5
        assert reversed_diff.new_index == 0

    def test_to_markdown_row_format(self) -> None:
        """Test markdown row output format."""
        diff = ModelContractFieldDiff(
            field_path="meta.name",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value("OldName"),
            new_value=ModelSchemaValue.from_value("NewName"),
            value_type="str",
        )
        row = diff.to_markdown_row()
        assert "| meta.name |" in row
        assert "modified" in row
        assert "OldName" in row
        assert "NewName" in row

    def test_to_markdown_row_moved_includes_indices(self) -> None:
        """Test markdown row includes indices for MOVED."""
        diff = ModelContractFieldDiff(
            field_path="transitions[0]",
            change_type=EnumContractDiffChangeType.MOVED,
            old_index=0,
            new_index=3,
            value_type="dict",
        )
        row = diff.to_markdown_row()
        assert "transitions[0]" in row
        assert "moved" in row
        assert "0 -> 3" in row

    def test_to_markdown_row_none_value(self) -> None:
        """Test markdown row handles None values."""
        diff = ModelContractFieldDiff(
            field_path="meta.field",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value("NewValue"),
            value_type="str",
        )
        row = diff.to_markdown_row()
        assert "-" in row  # None should become "-"

    def test_frozen_model(self) -> None:
        """Test model is immutable."""
        diff = ModelContractFieldDiff(
            field_path="meta.name",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value("Value"),
            value_type="str",
        )
        with pytest.raises(ValidationError):
            diff.field_path = "other.path"  # type: ignore[misc]

    def test_field_path_required(self) -> None:
        """Test field_path is required."""
        with pytest.raises(ValidationError):
            ModelContractFieldDiff(
                change_type=EnumContractDiffChangeType.ADDED,
                new_value=ModelSchemaValue.from_value("Value"),
                value_type="str",
            )  # type: ignore[call-arg]

    def test_field_path_min_length(self) -> None:
        """Test field_path has minimum length of 1."""
        with pytest.raises(ValidationError):
            ModelContractFieldDiff(
                field_path="",
                change_type=EnumContractDiffChangeType.ADDED,
                new_value=ModelSchemaValue.from_value("Value"),
                value_type="str",
            )

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelContractFieldDiff(
                field_path="meta.name",
                change_type=EnumContractDiffChangeType.ADDED,
                new_value=ModelSchemaValue.from_value("Value"),
                value_type="str",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_from_attributes_true(self) -> None:
        """Test model has from_attributes=True for pytest-xdist compatibility."""
        assert ModelContractFieldDiff.model_config.get("from_attributes") is True

    def test_value_type_default(self) -> None:
        """Test value_type has default of 'unknown'."""
        diff = ModelContractFieldDiff(
            field_path="meta.field",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value("Value"),
        )
        assert diff.value_type == "unknown"

    def test_index_negative_rejected(self) -> None:
        """Test that negative indices are rejected."""
        with pytest.raises(ValidationError):
            ModelContractFieldDiff(
                field_path="transitions[0]",
                change_type=EnumContractDiffChangeType.MOVED,
                old_index=-1,
                new_index=2,
                value_type="dict",
            )

    def test_integer_value(self) -> None:
        """Test diff with integer values."""
        diff = ModelContractFieldDiff(
            field_path="meta.count",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value(5),
            new_value=ModelSchemaValue.from_value(10),
            value_type="int",
        )
        assert diff.old_value is not None
        assert diff.old_value.to_value() == 5
        assert diff.new_value is not None
        assert diff.new_value.to_value() == 10

    def test_boolean_value(self) -> None:
        """Test diff with boolean values."""
        diff = ModelContractFieldDiff(
            field_path="meta.enabled",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value(False),
            new_value=ModelSchemaValue.from_value(True),
            value_type="bool",
        )
        assert diff.old_value is not None
        assert diff.old_value.to_value() is False
        assert diff.new_value is not None
        assert diff.new_value.to_value() is True

    def test_null_schema_value(self) -> None:
        """Test diff with null schema value."""
        diff = ModelContractFieldDiff(
            field_path="meta.optional",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value(None),
            new_value=ModelSchemaValue.from_value("now_set"),
            value_type="str",
        )
        assert diff.old_value is not None
        assert diff.old_value.to_value() is None
