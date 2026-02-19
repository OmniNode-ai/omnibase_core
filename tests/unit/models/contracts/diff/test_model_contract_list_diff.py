# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelContractListDiff."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff.model_contract_field_diff import (
    ModelContractFieldDiff,
)
from omnibase_core.models.contracts.diff.model_contract_list_diff import (
    ModelContractListDiff,
)


@pytest.mark.unit
class TestModelContractListDiff:
    """Test suite for ModelContractListDiff model."""

    @pytest.fixture
    def added_item(self) -> ModelContractFieldDiff:
        """Create an added item fixture."""
        return ModelContractFieldDiff(
            field_path="transitions.new_transition",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value({"name": "new_transition"}),
            value_type="dict",
        )

    @pytest.fixture
    def removed_item(self) -> ModelContractFieldDiff:
        """Create a removed item fixture."""
        return ModelContractFieldDiff(
            field_path="transitions.old_transition",
            change_type=EnumContractDiffChangeType.REMOVED,
            old_value=ModelSchemaValue.from_value({"name": "old_transition"}),
            value_type="dict",
        )

    @pytest.fixture
    def modified_item(self) -> ModelContractFieldDiff:
        """Create a modified item fixture."""
        return ModelContractFieldDiff(
            field_path="transitions.updated.target",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value("old_target"),
            new_value=ModelSchemaValue.from_value("new_target"),
            value_type="str",
        )

    @pytest.fixture
    def moved_item(self) -> ModelContractFieldDiff:
        """Create a moved item fixture."""
        return ModelContractFieldDiff(
            field_path="transitions[0]",
            change_type=EnumContractDiffChangeType.MOVED,
            old_index=0,
            new_index=2,
            value_type="dict",
        )

    def test_has_changes_with_added(self, added_item: ModelContractFieldDiff) -> None:
        """Test has_changes True when items added."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            added_items=[added_item],
        )
        assert list_diff.has_changes is True

    def test_has_changes_with_removed(
        self, removed_item: ModelContractFieldDiff
    ) -> None:
        """Test has_changes True when items removed."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            removed_items=[removed_item],
        )
        assert list_diff.has_changes is True

    def test_has_changes_with_modified(
        self, modified_item: ModelContractFieldDiff
    ) -> None:
        """Test has_changes True when items modified."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            modified_items=[modified_item],
        )
        assert list_diff.has_changes is True

    def test_has_changes_with_moved(self, moved_item: ModelContractFieldDiff) -> None:
        """Test has_changes True when items moved."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            moved_items=[moved_item],
        )
        assert list_diff.has_changes is True

    def test_has_changes_empty(self) -> None:
        """Test has_changes False when no changes."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            unchanged_count=5,
        )
        assert list_diff.has_changes is False

    def test_total_changes_count(
        self,
        added_item: ModelContractFieldDiff,
        removed_item: ModelContractFieldDiff,
        modified_item: ModelContractFieldDiff,
    ) -> None:
        """Test total_changes sums all change lists."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            added_items=[added_item, added_item],
            removed_items=[removed_item],
            modified_items=[modified_item, modified_item, modified_item],
            unchanged_count=10,
        )
        assert list_diff.total_changes == 6  # 2 + 1 + 3 + 0

    def test_total_changes_empty(self) -> None:
        """Test total_changes is 0 when no changes."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            unchanged_count=5,
        )
        assert list_diff.total_changes == 0

    def test_get_all_field_diffs(
        self,
        added_item: ModelContractFieldDiff,
        removed_item: ModelContractFieldDiff,
        modified_item: ModelContractFieldDiff,
        moved_item: ModelContractFieldDiff,
    ) -> None:
        """Test aggregates all diff lists."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            added_items=[added_item],
            removed_items=[removed_item],
            modified_items=[modified_item],
            moved_items=[moved_item],
        )
        all_diffs = list_diff.get_all_field_diffs()
        assert len(all_diffs) == 4
        assert added_item in all_diffs
        assert removed_item in all_diffs
        assert modified_item in all_diffs
        assert moved_item in all_diffs

    def test_get_all_field_diffs_empty(self) -> None:
        """Test get_all_field_diffs returns empty list when no changes."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            unchanged_count=5,
        )
        assert list_diff.get_all_field_diffs() == []

    def test_get_all_field_diffs_equals_total_changes(
        self,
        added_item: ModelContractFieldDiff,
        removed_item: ModelContractFieldDiff,
    ) -> None:
        """Test get_all_field_diffs length equals total_changes."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            added_items=[added_item, added_item],
            removed_items=[removed_item],
        )
        assert len(list_diff.get_all_field_diffs()) == list_diff.total_changes

    def test_frozen_model(self) -> None:
        """Test model is immutable."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
        )
        with pytest.raises(ValidationError):
            list_diff.field_path = "other.path"  # type: ignore[misc]

    def test_field_path_required(self) -> None:
        """Test field_path is required."""
        with pytest.raises(ValidationError):
            ModelContractListDiff(
                identity_key="name",
            )  # type: ignore[call-arg]

    def test_field_path_min_length(self) -> None:
        """Test field_path has minimum length of 1."""
        with pytest.raises(ValidationError):
            ModelContractListDiff(
                field_path="",
                identity_key="name",
            )

    def test_identity_key_required(self) -> None:
        """Test identity_key is required."""
        with pytest.raises(ValidationError):
            ModelContractListDiff(
                field_path="transitions",
            )  # type: ignore[call-arg]

    def test_identity_key_min_length(self) -> None:
        """Test identity_key has minimum length of 1."""
        with pytest.raises(ValidationError):
            ModelContractListDiff(
                field_path="transitions",
                identity_key="",
            )

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelContractListDiff(
                field_path="transitions",
                identity_key="name",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_from_attributes_true(self) -> None:
        """Test model has from_attributes=True for pytest-xdist compatibility."""
        assert ModelContractListDiff.model_config.get("from_attributes") is True

    def test_unchanged_count_default(self) -> None:
        """Test unchanged_count defaults to 0."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
        )
        assert list_diff.unchanged_count == 0

    def test_unchanged_count_negative_rejected(self) -> None:
        """Test unchanged_count cannot be negative."""
        with pytest.raises(ValidationError):
            ModelContractListDiff(
                field_path="transitions",
                identity_key="name",
                unchanged_count=-1,
            )

    def test_default_empty_lists(self) -> None:
        """Test default empty lists for all change types."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
        )
        assert list_diff.added_items == []
        assert list_diff.removed_items == []
        assert list_diff.modified_items == []
        assert list_diff.moved_items == []

    def test_computed_fields_serialization(
        self, added_item: ModelContractFieldDiff
    ) -> None:
        """Test computed fields are included in serialization."""
        list_diff = ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            added_items=[added_item],
        )
        data = list_diff.model_dump()
        assert "has_changes" in data
        assert "total_changes" in data
        assert data["has_changes"] is True
        assert data["total_changes"] == 1
