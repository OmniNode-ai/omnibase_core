# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive unit tests for ServiceDiffHistory.

Tests cover:
- Core CRUD operations (record, get, delete)
- Query convenience methods
- Statistics and aggregation
- Rendering operations
- Cleanup operations

OMN-1149: TDD tests for ServiceDiffHistory implementation.

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff import (
    ModelContractDiff,
    ModelContractFieldDiff,
)
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.services.diff.service_diff_history import ServiceDiffHistory
from omnibase_core.services.diff.service_diff_in_memory_store import (
    ServiceDiffInMemoryStore,
)

from .conftest import create_test_diff

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def store() -> ServiceDiffInMemoryStore:
    """Create a fresh in-memory store."""
    return ServiceDiffInMemoryStore()


@pytest.fixture
def service(store: ServiceDiffInMemoryStore) -> ServiceDiffHistory:
    """Create a service with in-memory backend."""
    return ServiceDiffHistory(store)


# ============================================================================
# Test: Core CRUD Operations
# ============================================================================


class TestServiceCRUD:
    """Test cases for core CRUD operations."""

    async def test_record_and_get(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service records and retrieves a diff."""
        diff_id = await service.record_diff(sample_diff)

        retrieved = await service.get_diff(diff_id)

        assert retrieved is not None
        assert retrieved.diff_id == sample_diff.diff_id
        assert retrieved.before_contract_name == sample_diff.before_contract_name

    async def test_record_returns_diff_id(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service record_diff returns the diff ID."""
        diff_id = await service.record_diff(sample_diff)

        assert diff_id == sample_diff.diff_id

    async def test_get_nonexistent_returns_none(
        self, service: ServiceDiffHistory
    ) -> None:
        """Service get_diff returns None for nonexistent diff."""
        result = await service.get_diff(uuid4())

        assert result is None

    async def test_delete_existing(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service deletes an existing diff."""
        await service.record_diff(sample_diff)

        result = await service.delete_diff(sample_diff.diff_id)

        assert result is True
        assert await service.get_diff(sample_diff.diff_id) is None

    async def test_delete_nonexistent(self, service: ServiceDiffHistory) -> None:
        """Service returns False when deleting nonexistent diff."""
        result = await service.delete_diff(uuid4())

        assert result is False


# ============================================================================
# Test: Query Operations
# ============================================================================


class TestServiceQuery:
    """Test cases for query operations."""

    async def test_query_diffs(
        self, service: ServiceDiffHistory, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Service query_diffs returns matching diffs."""
        for diff in sample_diffs:
            await service.record_diff(diff)

        query = ModelDiffQuery()
        results = await service.query_diffs(query)

        assert len(results) == len(sample_diffs)

    async def test_get_recent_diffs(
        self, service: ServiceDiffHistory, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Service get_recent_diffs returns most recent diffs."""
        for diff in sample_diffs:
            await service.record_diff(diff)

        results = await service.get_recent_diffs(limit=3)

        assert len(results) == 3

    async def test_get_recent_diffs_by_contract(
        self,
        service: ServiceDiffHistory,
        sample_diffs_multiple_contracts: list[ModelContractDiff],
    ) -> None:
        """Service get_recent_diffs filters by contract name."""
        for diff in sample_diffs_multiple_contracts:
            await service.record_diff(diff)

        results = await service.get_recent_diffs(contract_name="ContractA")

        assert len(results) == 2
        for result in results:
            assert (
                result.before_contract_name == "ContractA"
                or result.after_contract_name == "ContractA"
            )

    async def test_get_diffs_in_range(self, service: ServiceDiffHistory) -> None:
        """Service get_diffs_in_range returns diffs within time range."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        early = create_test_diff(computed_at=base_time - timedelta(hours=2))
        middle = create_test_diff(computed_at=base_time)
        late = create_test_diff(computed_at=base_time + timedelta(hours=2))

        await service.record_diff(early)
        await service.record_diff(middle)
        await service.record_diff(late)

        results = await service.get_diffs_in_range(
            start=base_time - timedelta(hours=1),
            end=base_time + timedelta(hours=1),
        )

        assert len(results) == 1
        assert results[0].diff_id == middle.diff_id

    async def test_get_diffs_in_range_invalid_range_raises_error(
        self, service: ServiceDiffHistory
    ) -> None:
        """Service get_diffs_in_range raises error for invalid range."""
        start = datetime(2025, 1, 2, tzinfo=UTC)
        end = datetime(2025, 1, 1, tzinfo=UTC)

        with pytest.raises(ModelOnexError):
            await service.get_diffs_in_range(start=start, end=end)

    async def test_get_contract_history(
        self,
        service: ServiceDiffHistory,
        sample_diffs_multiple_contracts: list[ModelContractDiff],
    ) -> None:
        """Service get_contract_history returns history for specific contract."""
        for diff in sample_diffs_multiple_contracts:
            await service.record_diff(diff)

        results = await service.get_contract_history("ContractA")

        assert len(results) == 2
        for result in results:
            assert (
                result.before_contract_name == "ContractA"
                or result.after_contract_name == "ContractA"
            )


# ============================================================================
# Test: Statistics and Aggregation
# ============================================================================


class TestServiceStatistics:
    """Test cases for statistics and aggregation."""

    async def test_get_diff_count(
        self, service: ServiceDiffHistory, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Service get_diff_count returns correct count."""
        for diff in sample_diffs:
            await service.record_diff(diff)

        count = await service.get_diff_count()

        assert count == len(sample_diffs)

    async def test_get_diff_count_by_contract(
        self,
        service: ServiceDiffHistory,
        sample_diffs_multiple_contracts: list[ModelContractDiff],
    ) -> None:
        """Service get_diff_count filters by contract name."""
        for diff in sample_diffs_multiple_contracts:
            await service.record_diff(diff)

        count = await service.get_diff_count(contract_name="ContractA")

        assert count == 2

    async def test_get_diff_count_since_time(self, service: ServiceDiffHistory) -> None:
        """Service get_diff_count filters by time."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        old_diff = create_test_diff(computed_at=base_time - timedelta(hours=2))
        new_diff = create_test_diff(computed_at=base_time)

        await service.record_diff(old_diff)
        await service.record_diff(new_diff)

        count = await service.get_diff_count(since=base_time - timedelta(hours=1))

        assert count == 1

    async def test_get_change_statistics(self, service: ServiceDiffHistory) -> None:
        """Service get_change_statistics returns aggregated statistics."""
        # Create diff with multiple change types
        diff = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="field1",
                    change_type=EnumContractDiffChangeType.ADDED,
                    new_value=ModelSchemaValue.from_value("added"),
                    value_type="str",
                ),
                ModelContractFieldDiff(
                    field_path="field2",
                    change_type=EnumContractDiffChangeType.MODIFIED,
                    old_value=ModelSchemaValue.from_value("old"),
                    new_value=ModelSchemaValue.from_value("new"),
                    value_type="str",
                ),
            ],
            list_diffs=[],
        )

        await service.record_diff(diff)

        stats = await service.get_change_statistics()

        assert stats["total_diffs"] == 1
        assert stats["total_changes"] == 2
        assert stats["added"] == 1
        assert stats["modified"] == 1

    async def test_get_change_statistics_by_contract(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service get_change_statistics filters by contract name."""
        await service.record_diff(sample_diff)

        # Create diff for different contract
        other_diff = create_test_diff(
            before_contract_name="OtherContract",
            after_contract_name="OtherContract",
        )
        await service.record_diff(other_diff)

        stats = await service.get_change_statistics(contract_name="ContractA")

        assert stats["total_diffs"] == 1


# ============================================================================
# Test: Rendering Operations
# ============================================================================


class TestServiceRendering:
    """Test cases for rendering operations."""

    async def test_render_diff_text(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service render_diff returns text format."""
        await service.record_diff(sample_diff)

        result = await service.render_diff(sample_diff.diff_id, EnumOutputFormat.TEXT)

        assert result is not None
        assert "ContractA" in result

    async def test_render_diff_markdown(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service render_diff returns markdown format."""
        await service.record_diff(sample_diff)

        result = await service.render_diff(
            sample_diff.diff_id, EnumOutputFormat.MARKDOWN
        )

        assert result is not None
        assert "##" in result or "Contract" in result

    async def test_render_diff_json(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service render_diff returns JSON format."""
        await service.record_diff(sample_diff)

        result = await service.render_diff(sample_diff.diff_id, EnumOutputFormat.JSON)

        assert result is not None
        assert "{" in result

    async def test_render_nonexistent_returns_none(
        self, service: ServiceDiffHistory
    ) -> None:
        """Service render_diff returns None for nonexistent diff."""
        result = await service.render_diff(uuid4())

        assert result is None

    async def test_render_recent_diffs(
        self, service: ServiceDiffHistory, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Service render_recent_diffs returns combined output."""
        for diff in sample_diffs:
            await service.record_diff(diff)

        result = await service.render_recent_diffs(limit=3)

        assert result is not None
        assert "ContractA" in result

    async def test_render_recent_diffs_empty(self, service: ServiceDiffHistory) -> None:
        """Service render_recent_diffs returns message when no diffs found."""
        result = await service.render_recent_diffs()

        assert result == "No diffs found."

    async def test_render_recent_diffs_json_format(
        self, service: ServiceDiffHistory, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Service render_recent_diffs returns JSON array for multiple diffs."""
        for diff in sample_diffs[:3]:
            await service.record_diff(diff)

        result = await service.render_recent_diffs(
            limit=3, output_format=EnumOutputFormat.JSON
        )

        assert result is not None
        assert result.startswith("[")
        assert result.endswith("]")


# ============================================================================
# Test: Cleanup Operations
# ============================================================================


class TestServiceCleanup:
    """Test cases for cleanup operations."""

    async def test_cleanup_old_diffs_by_datetime(
        self, service: ServiceDiffHistory
    ) -> None:
        """Service cleanup_old_diffs deletes diffs before datetime."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        old_diff = create_test_diff(computed_at=base_time - timedelta(days=30))
        new_diff = create_test_diff(computed_at=base_time)

        await service.record_diff(old_diff)
        await service.record_diff(new_diff)

        deleted = await service.cleanup_old_diffs(base_time - timedelta(days=1))

        assert deleted == 1
        assert await service.get_diff(old_diff.diff_id) is None
        assert await service.get_diff(new_diff.diff_id) is not None

    async def test_cleanup_old_diffs_by_timedelta(
        self, service: ServiceDiffHistory
    ) -> None:
        """Service cleanup_old_diffs deletes diffs older than timedelta."""
        # Note: This test uses current time, so we need to create a diff
        # that's old enough to be cleaned up
        now = datetime.now(UTC)
        old_diff = create_test_diff(computed_at=now - timedelta(days=60))

        await service.record_diff(old_diff)

        deleted = await service.cleanup_old_diffs(timedelta(days=30))

        assert deleted == 1
        assert await service.get_diff(old_diff.diff_id) is None

    async def test_cleanup_returns_zero_when_none_match(
        self, service: ServiceDiffHistory
    ) -> None:
        """Service cleanup_old_diffs returns 0 when no diffs match."""
        new_diff = create_test_diff()
        await service.record_diff(new_diff)

        deleted = await service.cleanup_old_diffs(timedelta(days=30))

        assert deleted == 0


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestServiceEdgeCases:
    """Test edge cases for the service."""

    async def test_empty_store_operations(self, service: ServiceDiffHistory) -> None:
        """Service handles empty store gracefully."""
        assert await service.get_diff_count() == 0
        assert await service.get_recent_diffs() == []

        stats = await service.get_change_statistics()
        assert stats["total_diffs"] == 0
        assert stats["total_changes"] == 0

    async def test_multiple_records_same_diff(
        self, service: ServiceDiffHistory, sample_diff: ModelContractDiff
    ) -> None:
        """Service handles recording same diff multiple times."""
        await service.record_diff(sample_diff)
        await service.record_diff(sample_diff)

        count = await service.get_diff_count()
        assert count == 1  # Should be 1 due to upsert semantics

    async def test_query_with_multiple_filters(
        self, service: ServiceDiffHistory
    ) -> None:
        """Service handles queries with multiple filters."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        diff = create_test_diff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            computed_at=base_time,
            with_changes=True,
        )
        await service.record_diff(diff)

        query = ModelDiffQuery(
            contract_name="ContractA",
            has_changes=True,
            computed_after=base_time - timedelta(hours=1),
        )
        results = await service.query_diffs(query)

        assert len(results) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
