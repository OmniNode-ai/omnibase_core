# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive unit tests for ServiceDiffInMemoryStore.

Tests cover:
- Put and get operations
- Query functionality with various filters
- Protocol compliance (ProtocolDiffStore)
- Memory management and cleanup
- Pagination

OMN-1149: TDD tests for ServiceDiffInMemoryStore implementation.

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_contract_diff_change_type import (
    EnumContractDiffChangeType,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.contracts.diff import (
    ModelContractDiff,
    ModelContractFieldDiff,
)
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
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
    """Create a fresh in-memory diff store."""
    return ServiceDiffInMemoryStore()


# ============================================================================
# Test: Protocol Compliance
# ============================================================================


class TestProtocolCompliance:
    """Test that ServiceDiffInMemoryStore implements ProtocolDiffStore."""

    def test_implements_protocol(self) -> None:
        """ServiceDiffInMemoryStore implements ProtocolDiffStore interface."""
        store = ServiceDiffInMemoryStore()
        assert isinstance(store, ProtocolDiffStore)

    def test_has_put_method(self, store: ServiceDiffInMemoryStore) -> None:
        """Store has async put method."""
        assert hasattr(store, "put")
        assert callable(store.put)

    def test_has_get_method(self, store: ServiceDiffInMemoryStore) -> None:
        """Store has async get method."""
        assert hasattr(store, "get")
        assert callable(store.get)

    def test_has_query_method(self, store: ServiceDiffInMemoryStore) -> None:
        """Store has async query method."""
        assert hasattr(store, "query")
        assert callable(store.query)

    def test_has_delete_method(self, store: ServiceDiffInMemoryStore) -> None:
        """Store has async delete method."""
        assert hasattr(store, "delete")
        assert callable(store.delete)

    def test_has_exists_method(self, store: ServiceDiffInMemoryStore) -> None:
        """Store has async exists method."""
        assert hasattr(store, "exists")
        assert callable(store.exists)

    def test_has_count_method(self, store: ServiceDiffInMemoryStore) -> None:
        """Store has async count method."""
        assert hasattr(store, "count")
        assert callable(store.count)


# ============================================================================
# Test: Put and Get Operations
# ============================================================================


class TestStorePutAndGet:
    """Test cases for put and get operations."""

    async def test_put_and_get(
        self, store: ServiceDiffInMemoryStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store correctly puts and gets diffs."""
        await store.put(sample_diff)

        retrieved = await store.get(sample_diff.diff_id)

        assert retrieved is not None
        assert retrieved.diff_id == sample_diff.diff_id
        assert retrieved.before_contract_name == sample_diff.before_contract_name
        assert retrieved.after_contract_name == sample_diff.after_contract_name

    async def test_get_nonexistent_returns_none(
        self, store: ServiceDiffInMemoryStore
    ) -> None:
        """Store returns None for nonexistent diff ID."""
        nonexistent_id = uuid4()

        retrieved = await store.get(nonexistent_id)

        assert retrieved is None

    async def test_put_multiple_diffs(self, store: ServiceDiffInMemoryStore) -> None:
        """Store can hold multiple diffs."""
        diffs = [create_test_diff() for _ in range(5)]

        for diff in diffs:
            await store.put(diff)

        # Verify all can be retrieved
        for diff in diffs:
            retrieved = await store.get(diff.diff_id)
            assert retrieved is not None
            assert retrieved.diff_id == diff.diff_id

    async def test_put_overwrites_existing(
        self, store: ServiceDiffInMemoryStore
    ) -> None:
        """Store overwrites diff with same ID (upsert semantics)."""
        diff_id = uuid4()

        diff_v1 = ModelContractDiff(
            diff_id=diff_id,
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[],
            list_diffs=[],
        )
        diff_v2 = ModelContractDiff(
            diff_id=diff_id,
            before_contract_name="ContractB",
            after_contract_name="ContractB",
            field_diffs=[],
            list_diffs=[],
        )

        await store.put(diff_v1)
        await store.put(diff_v2)

        retrieved = await store.get(diff_id)
        assert retrieved is not None
        # Should have the second diff's contract name
        assert retrieved.before_contract_name == "ContractB"

    async def test_put_preserves_diff_integrity(
        self, store: ServiceDiffInMemoryStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store preserves all diff fields."""
        await store.put(sample_diff)

        retrieved = await store.get(sample_diff.diff_id)

        assert retrieved is not None
        assert retrieved.diff_id == sample_diff.diff_id
        assert retrieved.before_contract_name == sample_diff.before_contract_name
        assert retrieved.after_contract_name == sample_diff.after_contract_name
        assert retrieved.computed_at == sample_diff.computed_at
        assert len(retrieved.field_diffs) == len(sample_diff.field_diffs)
        assert len(retrieved.list_diffs) == len(sample_diff.list_diffs)


# ============================================================================
# Test: Query Operations
# ============================================================================


class TestStoreQuery:
    """Test cases for query operations."""

    async def test_query_empty_filters(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store query with no filters returns all diffs."""
        for diff in sample_diffs:
            await store.put(diff)

        query = ModelDiffQuery()
        results = await store.query(query)

        assert len(results) == len(sample_diffs)

    async def test_query_empty_store(self, store: ServiceDiffInMemoryStore) -> None:
        """Store query returns empty list when store is empty."""
        query = ModelDiffQuery()
        results = await store.query(query)

        assert results == []

    async def test_query_by_contract_name(
        self,
        store: ServiceDiffInMemoryStore,
        sample_diffs_multiple_contracts: list[ModelContractDiff],
    ) -> None:
        """Store query filters by contract name correctly."""
        for diff in sample_diffs_multiple_contracts:
            await store.put(diff)

        query = ModelDiffQuery(contract_name="ContractA")
        results = await store.query(query)

        assert len(results) == 2
        for result in results:
            assert (
                result.before_contract_name == "ContractA"
                or result.after_contract_name == "ContractA"
            )

    async def test_query_by_before_contract_name(
        self,
        store: ServiceDiffInMemoryStore,
        sample_diffs_multiple_contracts: list[ModelContractDiff],
    ) -> None:
        """Store query filters by before_contract_name correctly."""
        for diff in sample_diffs_multiple_contracts:
            await store.put(diff)

        query = ModelDiffQuery(before_contract_name="ContractB")
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].before_contract_name == "ContractB"

    async def test_query_by_after_contract_name(
        self,
        store: ServiceDiffInMemoryStore,
        sample_diffs_multiple_contracts: list[ModelContractDiff],
    ) -> None:
        """Store query filters by after_contract_name correctly."""
        for diff in sample_diffs_multiple_contracts:
            await store.put(diff)

        query = ModelDiffQuery(after_contract_name="ContractC")
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].after_contract_name == "ContractC"

    async def test_query_by_time_range(self, store: ServiceDiffInMemoryStore) -> None:
        """Store query filters by time range correctly."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        early_diff = create_test_diff(computed_at=base_time - timedelta(hours=2))
        middle_diff = create_test_diff(computed_at=base_time)
        late_diff = create_test_diff(computed_at=base_time + timedelta(hours=2))

        await store.put(early_diff)
        await store.put(middle_diff)
        await store.put(late_diff)

        query = ModelDiffQuery(
            computed_after=base_time - timedelta(hours=1),
            computed_before=base_time + timedelta(hours=1),
        )
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].diff_id == middle_diff.diff_id

    async def test_query_by_has_changes(self, store: ServiceDiffInMemoryStore) -> None:
        """Store query filters by has_changes correctly."""
        diff_with_changes = create_test_diff(with_changes=True)
        diff_without_changes = create_test_diff(with_changes=False)

        await store.put(diff_with_changes)
        await store.put(diff_without_changes)

        query = ModelDiffQuery(has_changes=True)
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].has_changes is True

    async def test_query_pagination_limit(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store query respects limit parameter."""
        for diff in sample_diffs:
            await store.put(diff)

        query = ModelDiffQuery(limit=2)
        results = await store.query(query)

        assert len(results) == 2

    async def test_query_pagination_offset(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store query respects offset parameter."""
        for diff in sample_diffs:
            await store.put(diff)

        query = ModelDiffQuery(offset=3)
        results = await store.query(query)

        assert len(results) == 2  # 5 total - 3 offset = 2

    async def test_query_pagination_limit_and_offset(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store query correctly combines limit and offset."""
        for diff in sample_diffs:
            await store.put(diff)

        query = ModelDiffQuery(limit=2, offset=1)
        results = await store.query(query)

        assert len(results) == 2

    async def test_query_orders_by_computed_at_descending(
        self, store: ServiceDiffInMemoryStore
    ) -> None:
        """Store query orders results by computed_at descending."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        diff1 = create_test_diff(computed_at=base_time - timedelta(hours=2))
        diff2 = create_test_diff(computed_at=base_time)
        diff3 = create_test_diff(computed_at=base_time - timedelta(hours=1))

        # Insert in arbitrary order
        await store.put(diff1)
        await store.put(diff2)
        await store.put(diff3)

        query = ModelDiffQuery()
        results = await store.query(query)

        # Should be ordered: diff2 (newest), diff3, diff1 (oldest)
        assert results[0].diff_id == diff2.diff_id
        assert results[1].diff_id == diff3.diff_id
        assert results[2].diff_id == diff1.diff_id


# ============================================================================
# Test: Delete Operations
# ============================================================================


class TestStoreDelete:
    """Test cases for delete operations."""

    async def test_delete_existing(
        self, store: ServiceDiffInMemoryStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store deletes an existing diff."""
        await store.put(sample_diff)

        result = await store.delete(sample_diff.diff_id)

        assert result is True
        assert await store.get(sample_diff.diff_id) is None

    async def test_delete_nonexistent(self, store: ServiceDiffInMemoryStore) -> None:
        """Store returns False when deleting nonexistent diff."""
        nonexistent_id = uuid4()

        result = await store.delete(nonexistent_id)

        assert result is False

    async def test_delete_does_not_affect_others(
        self, store: ServiceDiffInMemoryStore
    ) -> None:
        """Deleting one diff does not affect other diffs."""
        diff1 = create_test_diff()
        diff2 = create_test_diff()

        await store.put(diff1)
        await store.put(diff2)

        await store.delete(diff1.diff_id)

        assert await store.get(diff1.diff_id) is None
        assert await store.get(diff2.diff_id) is not None


# ============================================================================
# Test: Exists Operations
# ============================================================================


class TestStoreExists:
    """Test cases for exists operations."""

    async def test_exists_returns_true_for_existing(
        self, store: ServiceDiffInMemoryStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store exists returns True for existing diff."""
        await store.put(sample_diff)

        result = await store.exists(sample_diff.diff_id)

        assert result is True

    async def test_exists_returns_false_for_nonexistent(
        self, store: ServiceDiffInMemoryStore
    ) -> None:
        """Store exists returns False for nonexistent diff."""
        nonexistent_id = uuid4()

        result = await store.exists(nonexistent_id)

        assert result is False


# ============================================================================
# Test: Count Operations
# ============================================================================


class TestStoreCount:
    """Test cases for count operations."""

    async def test_count_empty_store(self, store: ServiceDiffInMemoryStore) -> None:
        """Store count returns 0 for empty store."""
        count = await store.count()

        assert count == 0

    async def test_count_all_diffs(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store count returns correct number of diffs."""
        for diff in sample_diffs:
            await store.put(diff)

        count = await store.count()

        assert count == len(sample_diffs)

    async def test_count_with_filters(
        self,
        store: ServiceDiffInMemoryStore,
        sample_diffs_multiple_contracts: list[ModelContractDiff],
    ) -> None:
        """Store count with filters returns correct number."""
        for diff in sample_diffs_multiple_contracts:
            await store.put(diff)

        filters = ModelDiffQuery(contract_name="ContractA")
        count = await store.count(filters)

        assert count == 2

    async def test_count_ignores_pagination(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store count ignores limit and offset in filters."""
        for diff in sample_diffs:
            await store.put(diff)

        filters = ModelDiffQuery(limit=1, offset=10)
        count = await store.count(filters)

        assert count == len(sample_diffs)


# ============================================================================
# Test: Clear Operations
# ============================================================================


class TestStoreClear:
    """Test cases for clear operations."""

    async def test_clear_removes_all_diffs(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store clear removes all diffs."""
        for diff in sample_diffs:
            await store.put(diff)

        await store.clear()

        assert len(store) == 0
        for diff in sample_diffs:
            assert await store.get(diff.diff_id) is None


# ============================================================================
# Test: Get All Operations
# ============================================================================


class TestStoreGetAll:
    """Test cases for get_all operations."""

    async def test_get_all_empty_store(self, store: ServiceDiffInMemoryStore) -> None:
        """Store get_all returns empty list for empty store."""
        results = await store.get_all()

        assert results == []

    async def test_get_all_returns_all_diffs(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store get_all returns all stored diffs."""
        for diff in sample_diffs:
            await store.put(diff)

        results = await store.get_all()

        assert len(results) == len(sample_diffs)

    async def test_get_all_orders_by_computed_at_descending(
        self, store: ServiceDiffInMemoryStore
    ) -> None:
        """Store get_all orders results by computed_at descending."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        diff1 = create_test_diff(computed_at=base_time - timedelta(hours=2))
        diff2 = create_test_diff(computed_at=base_time)

        await store.put(diff1)
        await store.put(diff2)

        results = await store.get_all()

        assert results[0].diff_id == diff2.diff_id
        assert results[1].diff_id == diff1.diff_id


# ============================================================================
# Test: Len Operations
# ============================================================================


class TestStoreLen:
    """Test cases for __len__ operations."""

    def test_len_empty_store(self, store: ServiceDiffInMemoryStore) -> None:
        """Store len returns 0 for empty store."""
        assert len(store) == 0

    async def test_len_after_put(
        self, store: ServiceDiffInMemoryStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store len returns correct count after put."""
        await store.put(sample_diff)

        assert len(store) == 1

    async def test_len_after_delete(
        self, store: ServiceDiffInMemoryStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store len returns correct count after delete."""
        await store.put(sample_diff)
        await store.delete(sample_diff.diff_id)

        assert len(store) == 0


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestStoreEdgeCases:
    """Test edge cases for the store."""

    async def test_query_offset_beyond_total(
        self, store: ServiceDiffInMemoryStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Query with offset beyond total returns empty list."""
        for diff in sample_diffs:
            await store.put(diff)

        query = ModelDiffQuery(offset=100)
        results = await store.query(query)

        assert results == []

    async def test_concurrent_operations(self, store: ServiceDiffInMemoryStore) -> None:
        """Store handles concurrent put operations."""
        import asyncio

        async def put_diff():
            diff = create_test_diff()
            await store.put(diff)
            return diff.diff_id

        # Run puts concurrently
        put_tasks = [put_diff() for _ in range(10)]
        diff_ids = await asyncio.gather(*put_tasks)

        # All should be stored
        assert len(set(diff_ids)) == 10

    async def test_query_by_change_types(self, store: ServiceDiffInMemoryStore) -> None:
        """Store query filters by change types correctly."""
        # Create diff with ADDED change
        diff_added = ModelContractDiff(
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="new_field",
                    change_type=EnumContractDiffChangeType.ADDED,
                    new_value=ModelSchemaValue.from_value("value"),
                    value_type="str",
                ),
            ],
            list_diffs=[],
        )

        # Create diff with MODIFIED change
        diff_modified = ModelContractDiff(
            before_contract_name="ContractB",
            after_contract_name="ContractB",
            field_diffs=[
                ModelContractFieldDiff(
                    field_path="changed_field",
                    change_type=EnumContractDiffChangeType.MODIFIED,
                    old_value=ModelSchemaValue.from_value("old"),
                    new_value=ModelSchemaValue.from_value("new"),
                    value_type="str",
                ),
            ],
            list_diffs=[],
        )

        await store.put(diff_added)
        await store.put(diff_modified)

        query = ModelDiffQuery(
            change_types=frozenset({EnumContractDiffChangeType.ADDED})
        )
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].diff_id == diff_added.diff_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
