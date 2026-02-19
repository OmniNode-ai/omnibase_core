# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelContractDiff."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff.model_contract_diff import ModelContractDiff
from omnibase_core.models.contracts.diff.model_contract_field_diff import (
    ModelContractFieldDiff,
)
from omnibase_core.models.contracts.diff.model_contract_list_diff import (
    ModelContractListDiff,
)


@pytest.mark.unit
class TestModelContractDiff:
    """Test suite for ModelContractDiff model."""

    @pytest.fixture
    def added_field_diff(self) -> ModelContractFieldDiff:
        """Create an added field diff fixture."""
        return ModelContractFieldDiff(
            field_path="meta.new_field",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value("new_value"),
            value_type="str",
        )

    @pytest.fixture
    def removed_field_diff(self) -> ModelContractFieldDiff:
        """Create a removed field diff fixture."""
        return ModelContractFieldDiff(
            field_path="meta.old_field",
            change_type=EnumContractDiffChangeType.REMOVED,
            old_value=ModelSchemaValue.from_value("old_value"),
            value_type="str",
        )

    @pytest.fixture
    def modified_field_diff(self) -> ModelContractFieldDiff:
        """Create a modified field diff fixture."""
        return ModelContractFieldDiff(
            field_path="meta.version",
            change_type=EnumContractDiffChangeType.MODIFIED,
            old_value=ModelSchemaValue.from_value("1.0.0"),
            new_value=ModelSchemaValue.from_value("2.0.0"),
            value_type="str",
        )

    @pytest.fixture
    def unchanged_field_diff(self) -> ModelContractFieldDiff:
        """Create an unchanged field diff fixture."""
        value = ModelSchemaValue.from_value("same_value")
        return ModelContractFieldDiff(
            field_path="meta.name",
            change_type=EnumContractDiffChangeType.UNCHANGED,
            old_value=value,
            new_value=value,
            value_type="str",
        )

    @pytest.fixture
    def list_diff_with_changes(self) -> ModelContractListDiff:
        """Create a list diff with changes fixture."""
        added_item = ModelContractFieldDiff(
            field_path="transitions.new_transition",
            change_type=EnumContractDiffChangeType.ADDED,
            new_value=ModelSchemaValue.from_value({"name": "new"}),
            value_type="dict",
        )
        return ModelContractListDiff(
            field_path="transitions",
            identity_key="name",
            added_items=[added_item],
            unchanged_count=5,
        )

    @pytest.fixture
    def list_diff_no_changes(self) -> ModelContractListDiff:
        """Create a list diff without changes fixture."""
        return ModelContractListDiff(
            field_path="states",
            identity_key="name",
            unchanged_count=3,
        )

    def test_diff_id_auto_generated(self) -> None:
        """Test diff_id is generated automatically."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        assert isinstance(diff.diff_id, UUID)

    def test_diff_id_unique(self) -> None:
        """Test each diff gets a unique diff_id."""
        diff1 = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        diff2 = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        assert diff1.diff_id != diff2.diff_id

    def test_has_changes_with_field_diffs(
        self, added_field_diff: ModelContractFieldDiff
    ) -> None:
        """Test has_changes True with field changes."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[added_field_diff],
        )
        assert diff.has_changes is True

    def test_has_changes_with_list_diffs(
        self, list_diff_with_changes: ModelContractListDiff
    ) -> None:
        """Test has_changes True with list changes."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            list_diffs=[list_diff_with_changes],
        )
        assert diff.has_changes is True

    def test_has_changes_excludes_unchanged(
        self, unchanged_field_diff: ModelContractFieldDiff
    ) -> None:
        """Test has_changes ignores UNCHANGED entries."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[unchanged_field_diff],
        )
        assert diff.has_changes is False

    def test_has_changes_empty(self) -> None:
        """Test has_changes False with no changes."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        assert diff.has_changes is False

    def test_has_changes_with_unchanged_list_diff(
        self, list_diff_no_changes: ModelContractListDiff
    ) -> None:
        """Test has_changes False with list diff that has no changes."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            list_diffs=[list_diff_no_changes],
        )
        assert diff.has_changes is False

    def test_total_changes_sums_all(
        self,
        added_field_diff: ModelContractFieldDiff,
        removed_field_diff: ModelContractFieldDiff,
        list_diff_with_changes: ModelContractListDiff,
    ) -> None:
        """Test total_changes counts all changes."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[added_field_diff, removed_field_diff],
            list_diffs=[list_diff_with_changes],
        )
        # 2 field diffs + 1 added item in list diff = 3
        assert diff.total_changes == 3

    def test_total_changes_excludes_unchanged(
        self,
        added_field_diff: ModelContractFieldDiff,
        unchanged_field_diff: ModelContractFieldDiff,
    ) -> None:
        """Test total_changes excludes UNCHANGED entries."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[added_field_diff, unchanged_field_diff],
        )
        assert diff.total_changes == 1

    def test_change_summary_by_type(
        self,
        added_field_diff: ModelContractFieldDiff,
        removed_field_diff: ModelContractFieldDiff,
        modified_field_diff: ModelContractFieldDiff,
    ) -> None:
        """Test change_summary groups by change type."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[added_field_diff, removed_field_diff, modified_field_diff],
        )
        summary = diff.change_summary
        assert summary["added"] == 1
        assert summary["removed"] == 1
        assert summary["modified"] == 1
        assert summary["moved"] == 0
        assert summary["unchanged"] == 0

    def test_change_summary_includes_list_diffs(
        self, list_diff_with_changes: ModelContractListDiff
    ) -> None:
        """Test change_summary includes changes from list diffs."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            list_diffs=[list_diff_with_changes],
        )
        summary = diff.change_summary
        assert summary["added"] == 1
        assert summary["unchanged"] == 5  # From list_diff unchanged_count

    def test_get_all_field_diffs_includes_list_diffs(
        self,
        added_field_diff: ModelContractFieldDiff,
        list_diff_with_changes: ModelContractListDiff,
    ) -> None:
        """Test get_all_field_diffs includes nested list diffs."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[added_field_diff],
            list_diffs=[list_diff_with_changes],
        )
        all_diffs = diff.get_all_field_diffs()
        assert len(all_diffs) == 2
        assert added_field_diff in all_diffs

    def test_get_all_field_diffs_empty(self) -> None:
        """Test get_all_field_diffs returns empty list when no changes."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        assert diff.get_all_field_diffs() == []

    def test_to_markdown_table_header(
        self, added_field_diff: ModelContractFieldDiff
    ) -> None:
        """Test markdown table has correct header."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractB",
            field_diffs=[added_field_diff],
        )
        markdown = diff.to_markdown_table()
        assert "## Contract Diff: ContractA -> ContractB" in markdown
        assert "### Summary" in markdown
        assert "| Field Path | Change Type | Old Value | New Value |" in markdown

    def test_to_markdown_table_rows(
        self,
        added_field_diff: ModelContractFieldDiff,
        modified_field_diff: ModelContractFieldDiff,
    ) -> None:
        """Test markdown table has rows for each change."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[added_field_diff, modified_field_diff],
        )
        markdown = diff.to_markdown_table()
        assert "meta.new_field" in markdown
        assert "meta.version" in markdown
        assert "added" in markdown
        assert "modified" in markdown

    def test_to_markdown_table_no_changes(self) -> None:
        """Test markdown table message when no changes."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        markdown = diff.to_markdown_table()
        assert "*No changes detected.*" in markdown

    def test_to_markdown_table_excludes_unchanged(
        self, unchanged_field_diff: ModelContractFieldDiff
    ) -> None:
        """Test markdown table excludes UNCHANGED field diffs."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[unchanged_field_diff],
        )
        markdown = diff.to_markdown_table()
        # Should not include unchanged field in the table rows
        assert "*No changes detected.*" in markdown

    def test_to_markdown_table_includes_list_diffs(
        self, list_diff_with_changes: ModelContractListDiff
    ) -> None:
        """Test markdown table includes list diff sections."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            list_diffs=[list_diff_with_changes],
        )
        markdown = diff.to_markdown_table()
        assert "### List Changes:" in markdown
        assert "transitions" in markdown
        assert "Identity Key:" in markdown

    def test_frozen_model(self) -> None:
        """Test model is immutable."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        with pytest.raises(ValidationError):
            diff.before_contract_name = "ContractB"  # type: ignore[misc]

    def test_before_contract_name_required(self) -> None:
        """Test before_contract_name is required."""
        with pytest.raises(ValidationError):
            ModelContractDiff(
                after_contract_name="ContractA",
            )  # type: ignore[call-arg]

    def test_after_contract_name_required(self) -> None:
        """Test after_contract_name is required."""
        with pytest.raises(ValidationError):
            ModelContractDiff(
                before_contract_name="ContractA",
            )  # type: ignore[call-arg]

    def test_contract_name_min_length(self) -> None:
        """Test contract names have minimum length of 1."""
        with pytest.raises(ValidationError):
            ModelContractDiff(
                before_contract_name="",
                after_contract_name="ContractA",
            )

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelContractDiff(
                before_contract_name="ContractA",
                after_contract_name="ContractA",
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    def test_from_attributes_true(self) -> None:
        """Test model has from_attributes=True for pytest-xdist compatibility."""
        assert ModelContractDiff.model_config.get("from_attributes") is True

    def test_computed_at_auto_generated(self) -> None:
        """Test computed_at is automatically set."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        assert diff.computed_at is not None

    def test_fingerprints_optional(self) -> None:
        """Test fingerprints are optional."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        assert diff.before_fingerprint is None
        assert diff.after_fingerprint is None

    def test_default_empty_lists(self) -> None:
        """Test default empty lists for field_diffs and list_diffs."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
        )
        assert diff.field_diffs == []
        assert diff.list_diffs == []

    def test_computed_fields_serialization(
        self, added_field_diff: ModelContractFieldDiff
    ) -> None:
        """Test computed fields are included in serialization."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[added_field_diff],
        )
        data = diff.model_dump()
        assert "has_changes" in data
        assert "total_changes" in data
        assert "change_summary" in data
        assert data["has_changes"] is True
        assert data["total_changes"] == 1


@pytest.mark.unit
class TestModelContractDiffEdgeCases:
    """Test edge cases for ModelContractDiff."""

    def test_many_field_diffs(self) -> None:
        """Test with many field diffs."""
        field_diffs = [
            ModelContractFieldDiff(
                field_path=f"field_{i}",
                change_type=EnumContractDiffChangeType.ADDED,
                new_value=ModelSchemaValue.from_value(f"value_{i}"),
                value_type="str",
            )
            for i in range(100)
        ]
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=field_diffs,
        )
        assert diff.total_changes == 100
        assert diff.change_summary["added"] == 100

    def test_many_list_diffs(self) -> None:
        """Test with many list diffs."""
        list_diffs = [
            ModelContractListDiff(
                field_path=f"list_{i}",
                identity_key="id",
                added_items=[
                    ModelContractFieldDiff(
                        field_path=f"list_{i}.item",
                        change_type=EnumContractDiffChangeType.ADDED,
                        new_value=ModelSchemaValue.from_value({"id": i}),
                        value_type="dict",
                    )
                ],
            )
            for i in range(50)
        ]
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            list_diffs=list_diffs,
        )
        assert diff.total_changes == 50
        assert len(diff.get_all_field_diffs()) == 50

    def test_mixed_change_types(self) -> None:
        """Test with all change types present."""
        value = ModelSchemaValue.from_value("value")
        field_diffs = [
            ModelContractFieldDiff(
                field_path="added",
                change_type=EnumContractDiffChangeType.ADDED,
                new_value=value,
                value_type="str",
            ),
            ModelContractFieldDiff(
                field_path="removed",
                change_type=EnumContractDiffChangeType.REMOVED,
                old_value=value,
                value_type="str",
            ),
            ModelContractFieldDiff(
                field_path="modified",
                change_type=EnumContractDiffChangeType.MODIFIED,
                old_value=value,
                new_value=value,
                value_type="str",
            ),
            ModelContractFieldDiff(
                field_path="unchanged",
                change_type=EnumContractDiffChangeType.UNCHANGED,
                old_value=value,
                new_value=value,
                value_type="str",
            ),
        ]
        list_diffs = [
            ModelContractListDiff(
                field_path="items",
                identity_key="id",
                moved_items=[
                    ModelContractFieldDiff(
                        field_path="items[0]",
                        change_type=EnumContractDiffChangeType.MOVED,
                        old_index=0,
                        new_index=2,
                        value_type="dict",
                    )
                ],
            )
        ]
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=field_diffs,
            list_diffs=list_diffs,
        )
        summary = diff.change_summary
        assert summary["added"] == 1
        assert summary["removed"] == 1
        assert summary["modified"] == 1
        assert summary["moved"] == 1
        assert summary["unchanged"] == 1
        assert diff.total_changes == 4  # Excludes unchanged
