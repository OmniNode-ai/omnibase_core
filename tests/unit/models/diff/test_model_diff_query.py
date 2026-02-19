# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive unit tests for ModelDiffQuery.

Tests cover:
- Model validation
- matches_diff logic
- Filter combinations
- Edge cases

OMN-1149: TDD tests for ModelDiffQuery implementation.

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff import (
    ModelContractDiff,
    ModelContractFieldDiff,
)
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery

pytestmark = [pytest.mark.unit]


# ============================================================================
# Helper Functions
# ============================================================================


def create_test_diff(
    *,
    before_contract_name: str = "ContractA",
    after_contract_name: str = "ContractA",
    computed_at: datetime | None = None,
    with_changes: bool = True,
    change_type: EnumContractDiffChangeType = EnumContractDiffChangeType.MODIFIED,
) -> ModelContractDiff:
    """Create a test diff with specified parameters."""
    field_diffs: list[ModelContractFieldDiff] = []

    if with_changes:
        if change_type == EnumContractDiffChangeType.ADDED:
            field_diffs = [
                ModelContractFieldDiff(
                    field_path="new_field",
                    change_type=change_type,
                    new_value=ModelSchemaValue.from_value("added"),
                    value_type="str",
                ),
            ]
        elif change_type == EnumContractDiffChangeType.REMOVED:
            field_diffs = [
                ModelContractFieldDiff(
                    field_path="old_field",
                    change_type=change_type,
                    old_value=ModelSchemaValue.from_value("removed"),
                    value_type="str",
                ),
            ]
        else:
            field_diffs = [
                ModelContractFieldDiff(
                    field_path="changed_field",
                    change_type=EnumContractDiffChangeType.MODIFIED,
                    old_value=ModelSchemaValue.from_value("old"),
                    new_value=ModelSchemaValue.from_value("new"),
                    value_type="str",
                ),
            ]

    kwargs: dict = {
        "before_contract_name": before_contract_name,
        "after_contract_name": after_contract_name,
        "field_diffs": field_diffs,
        "list_diffs": [],
    }

    if computed_at is not None:
        kwargs["computed_at"] = computed_at

    return ModelContractDiff(**kwargs)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_diff() -> ModelContractDiff:
    """Create a sample diff with one field change."""
    return create_test_diff()


@pytest.fixture
def sample_diff_no_changes() -> ModelContractDiff:
    """Create a sample diff with no changes."""
    return create_test_diff(with_changes=False)


# ============================================================================
# Test: Model Validation
# ============================================================================


class TestModelValidation:
    """Test cases for model validation."""

    def test_default_values(self) -> None:
        """Query has correct default values."""
        query = ModelDiffQuery()

        assert query.before_contract_name is None
        assert query.after_contract_name is None
        assert query.contract_name is None
        assert query.computed_after is None
        assert query.computed_before is None
        assert query.change_types is None
        assert query.has_changes is None
        assert query.limit == 100
        assert query.offset == 0

    def test_limit_bounds(self) -> None:
        """Query validates limit bounds."""
        # Valid limits
        ModelDiffQuery(limit=1)
        ModelDiffQuery(limit=500)
        ModelDiffQuery(limit=1000)

        # Invalid: too low
        with pytest.raises(ValidationError):
            ModelDiffQuery(limit=0)

        # Invalid: too high
        with pytest.raises(ValidationError):
            ModelDiffQuery(limit=1001)

    def test_offset_non_negative(self) -> None:
        """Query validates offset is non-negative."""
        ModelDiffQuery(offset=0)
        ModelDiffQuery(offset=100)

        with pytest.raises(ValidationError):
            ModelDiffQuery(offset=-1)

    def test_time_range_validation(self) -> None:
        """Query validates computed_before is not before computed_after."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Valid: computed_before after computed_after
        ModelDiffQuery(
            computed_after=base_time,
            computed_before=base_time + timedelta(hours=1),
        )

        # Valid: only computed_after
        ModelDiffQuery(computed_after=base_time)

        # Valid: only computed_before
        ModelDiffQuery(computed_before=base_time)

        # Invalid: computed_before before computed_after
        with pytest.raises(ValidationError):
            ModelDiffQuery(
                computed_after=base_time,
                computed_before=base_time - timedelta(hours=1),
            )

    def test_immutable_model(self) -> None:
        """Query model is immutable (frozen)."""
        query = ModelDiffQuery()

        with pytest.raises(ValidationError):
            query.limit = 50  # type: ignore[misc]

    def test_change_types_empty_frozenset_raises(self) -> None:
        """Query rejects empty change_types frozenset."""
        with pytest.raises(ValidationError) as exc_info:
            ModelDiffQuery(change_types=frozenset())

        assert "change_types must be non-empty when specified" in str(exc_info.value)
        assert "Use None to match all change types" in str(exc_info.value)

    def test_change_types_non_empty_frozenset_valid(self) -> None:
        """Query accepts non-empty change_types frozenset."""
        query = ModelDiffQuery(
            change_types=frozenset({EnumContractDiffChangeType.ADDED})
        )

        assert query.change_types == frozenset({EnumContractDiffChangeType.ADDED})

    def test_change_types_none_valid(self) -> None:
        """Query accepts None for change_types (default)."""
        query = ModelDiffQuery(change_types=None)

        assert query.change_types is None


# ============================================================================
# Test: matches_diff - Contract Name Filters
# ============================================================================


class TestMatchesContractName:
    """Test cases for contract name filtering."""

    def test_matches_diff_contract_name(self, sample_diff: ModelContractDiff) -> None:
        """Query matches diffs by contract name (either before or after)."""
        query = ModelDiffQuery(contract_name="ContractA")

        assert query.matches_diff(sample_diff) is True

    def test_matches_diff_contract_name_no_match(
        self, sample_diff: ModelContractDiff
    ) -> None:
        """Query does not match diffs with different contract name."""
        query = ModelDiffQuery(contract_name="ContractB")

        assert query.matches_diff(sample_diff) is False

    def test_matches_diff_before_contract_name(
        self, sample_diff: ModelContractDiff
    ) -> None:
        """Query matches diffs by before_contract_name."""
        query = ModelDiffQuery(before_contract_name="ContractA")

        assert query.matches_diff(sample_diff) is True

    def test_matches_diff_before_contract_name_no_match(
        self, sample_diff: ModelContractDiff
    ) -> None:
        """Query does not match diffs with different before_contract_name."""
        query = ModelDiffQuery(before_contract_name="ContractB")

        assert query.matches_diff(sample_diff) is False

    def test_matches_diff_after_contract_name(
        self, sample_diff: ModelContractDiff
    ) -> None:
        """Query matches diffs by after_contract_name."""
        query = ModelDiffQuery(after_contract_name="ContractA")

        assert query.matches_diff(sample_diff) is True

    def test_matches_diff_after_contract_name_no_match(
        self, sample_diff: ModelContractDiff
    ) -> None:
        """Query does not match diffs with different after_contract_name."""
        query = ModelDiffQuery(after_contract_name="ContractB")

        assert query.matches_diff(sample_diff) is False

    def test_matches_diff_rename(self) -> None:
        """Query contract_name matches either before or after in rename."""
        diff = ModelContractDiff(
            before_contract_name="OldName",
            after_contract_name="NewName",
            field_diffs=[],
            list_diffs=[],
        )

        query_old = ModelDiffQuery(contract_name="OldName")
        query_new = ModelDiffQuery(contract_name="NewName")

        assert query_old.matches_diff(diff) is True
        assert query_new.matches_diff(diff) is True


# ============================================================================
# Test: matches_diff - Time Range Filters
# ============================================================================


class TestMatchesTimeRange:
    """Test cases for time range filtering."""

    def test_matches_diff_computed_after(self) -> None:
        """Query matches diffs computed at or after computed_after."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        diff = create_test_diff(computed_at=base_time)

        query_before = ModelDiffQuery(computed_after=base_time - timedelta(hours=1))
        query_exact = ModelDiffQuery(computed_after=base_time)
        query_after = ModelDiffQuery(computed_after=base_time + timedelta(hours=1))

        assert query_before.matches_diff(diff) is True
        assert query_exact.matches_diff(diff) is True
        assert query_after.matches_diff(diff) is False

    def test_matches_diff_computed_before(self) -> None:
        """Query matches diffs computed before computed_before (exclusive)."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        diff = create_test_diff(computed_at=base_time)

        query_before = ModelDiffQuery(computed_before=base_time - timedelta(hours=1))
        query_exact = ModelDiffQuery(computed_before=base_time)
        query_after = ModelDiffQuery(computed_before=base_time + timedelta(hours=1))

        assert query_before.matches_diff(diff) is False
        assert query_exact.matches_diff(diff) is False  # Exclusive
        assert query_after.matches_diff(diff) is True

    def test_matches_diff_time_range(self) -> None:
        """Query matches diffs within time range."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        diff = create_test_diff(computed_at=base_time)

        query = ModelDiffQuery(
            computed_after=base_time - timedelta(hours=1),
            computed_before=base_time + timedelta(hours=1),
        )

        assert query.matches_diff(diff) is True


# ============================================================================
# Test: matches_diff - has_changes Filter
# ============================================================================


class TestMatchesHasChanges:
    """Test cases for has_changes filtering."""

    def test_matches_diff_has_changes_true(
        self, sample_diff: ModelContractDiff
    ) -> None:
        """Query matches diffs with changes when has_changes=True."""
        query = ModelDiffQuery(has_changes=True)

        assert query.matches_diff(sample_diff) is True

    def test_matches_diff_has_changes_false(
        self, sample_diff_no_changes: ModelContractDiff
    ) -> None:
        """Query matches diffs without changes when has_changes=False."""
        query = ModelDiffQuery(has_changes=False)

        assert query.matches_diff(sample_diff_no_changes) is True

    def test_matches_diff_has_changes_no_match(
        self, sample_diff: ModelContractDiff, sample_diff_no_changes: ModelContractDiff
    ) -> None:
        """Query does not match when has_changes doesn't match."""
        query_true = ModelDiffQuery(has_changes=True)
        query_false = ModelDiffQuery(has_changes=False)

        assert query_true.matches_diff(sample_diff_no_changes) is False
        assert query_false.matches_diff(sample_diff) is False

    def test_matches_diff_has_changes_none(
        self, sample_diff: ModelContractDiff, sample_diff_no_changes: ModelContractDiff
    ) -> None:
        """Query with has_changes=None matches all diffs."""
        query = ModelDiffQuery(has_changes=None)

        assert query.matches_diff(sample_diff) is True
        assert query.matches_diff(sample_diff_no_changes) is True


# ============================================================================
# Test: matches_diff - Change Types Filter
# ============================================================================


class TestMatchesChangeTypes:
    """Test cases for change_types filtering."""

    def test_matches_diff_change_types(self) -> None:
        """Query matches diffs with specified change types."""
        diff_added = create_test_diff(change_type=EnumContractDiffChangeType.ADDED)
        diff_modified = create_test_diff(
            change_type=EnumContractDiffChangeType.MODIFIED
        )

        query = ModelDiffQuery(
            change_types=frozenset({EnumContractDiffChangeType.ADDED})
        )

        assert query.matches_diff(diff_added) is True
        assert query.matches_diff(diff_modified) is False

    def test_matches_diff_change_types_multiple(self) -> None:
        """Query matches diffs with any of multiple change types."""
        diff_added = create_test_diff(change_type=EnumContractDiffChangeType.ADDED)
        diff_removed = create_test_diff(change_type=EnumContractDiffChangeType.REMOVED)

        query = ModelDiffQuery(
            change_types=frozenset(
                {EnumContractDiffChangeType.ADDED, EnumContractDiffChangeType.REMOVED}
            )
        )

        assert query.matches_diff(diff_added) is True
        assert query.matches_diff(diff_removed) is True

    def test_matches_diff_change_types_no_match(self) -> None:
        """Query does not match diffs without specified change types."""
        diff_modified = create_test_diff(
            change_type=EnumContractDiffChangeType.MODIFIED
        )

        query = ModelDiffQuery(
            change_types=frozenset({EnumContractDiffChangeType.ADDED})
        )

        assert query.matches_diff(diff_modified) is False


# ============================================================================
# Test: Utility Methods
# ============================================================================


class TestUtilityMethods:
    """Test cases for utility methods."""

    def test_has_time_filter(self) -> None:
        """Query has_time_filter returns correct value."""
        query_none = ModelDiffQuery()
        query_after = ModelDiffQuery(computed_after=datetime.now(UTC))
        query_before = ModelDiffQuery(computed_before=datetime.now(UTC))

        assert query_none.has_time_filter() is False
        assert query_after.has_time_filter() is True
        assert query_before.has_time_filter() is True

    def test_has_filters(self) -> None:
        """Query has_filters returns correct value."""
        query_none = ModelDiffQuery()
        query_contract = ModelDiffQuery(contract_name="ContractA")
        query_changes = ModelDiffQuery(has_changes=True)

        assert query_none.has_filters() is False
        assert query_contract.has_filters() is True
        assert query_changes.has_filters() is True

    def test_str_representation(self) -> None:
        """Query __str__ returns human-readable representation."""
        query = ModelDiffQuery(
            contract_name="ContractA",
            has_changes=True,
            limit=50,
        )

        result = str(query)

        assert "ContractA" in result
        assert "has_changes=True" in result
        assert "limit=50" in result


# ============================================================================
# Test: Combined Filters
# ============================================================================


class TestCombinedFilters:
    """Test cases for combined filter logic."""

    def test_matches_diff_all_filters(self) -> None:
        """Query matches diffs meeting all filter criteria."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        diff = create_test_diff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            computed_at=base_time,
            with_changes=True,
        )

        query = ModelDiffQuery(
            contract_name="ContractA",
            computed_after=base_time - timedelta(hours=1),
            computed_before=base_time + timedelta(hours=1),
            has_changes=True,
        )

        assert query.matches_diff(diff) is True

    def test_matches_diff_fails_one_filter(self) -> None:
        """Query does not match if any filter fails."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        diff = create_test_diff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            computed_at=base_time,
            with_changes=True,
        )

        # Contract name doesn't match
        query_wrong_contract = ModelDiffQuery(
            contract_name="ContractB",
            has_changes=True,
        )

        # Time doesn't match
        query_wrong_time = ModelDiffQuery(
            contract_name="ContractA",
            computed_before=base_time - timedelta(hours=1),
        )

        assert query_wrong_contract.matches_diff(diff) is False
        assert query_wrong_time.matches_diff(diff) is False


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_query_matches_all(self) -> None:
        """Empty query matches all diffs."""
        query = ModelDiffQuery()
        diff = create_test_diff()

        assert query.matches_diff(diff) is True

    def test_diff_with_no_field_diffs(self) -> None:
        """Query handles diffs with no field diffs."""
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[],
            list_diffs=[],
        )

        query = ModelDiffQuery(has_changes=False)

        assert query.matches_diff(diff) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
