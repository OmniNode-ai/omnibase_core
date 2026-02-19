# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive unit tests for ServiceDiffFileStore.

Tests cover:
- Put and get operations
- Flush and file persistence
- Query functionality
- Buffer management
- File I/O edge cases

OMN-1149: TDD tests for ServiceDiffFileStore implementation.

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from omnibase_core.errors import ModelOnexError
from omnibase_core.models.contracts.diff import ModelContractDiff
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
from omnibase_core.services.diff.service_diff_file_store import ServiceDiffFileStore

from .conftest import create_test_diff

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def store(tmp_path: Path) -> ServiceDiffFileStore:
    """Create a fresh file-based diff store."""
    return ServiceDiffFileStore(base_path=tmp_path, buffer_size=10)


@pytest.fixture
def store_small_buffer(tmp_path: Path) -> ServiceDiffFileStore:
    """Create a store with small buffer for testing auto-flush."""
    return ServiceDiffFileStore(base_path=tmp_path, buffer_size=2)


# ============================================================================
# Test: Protocol Compliance
# ============================================================================


class TestProtocolCompliance:
    """Test that ServiceDiffFileStore implements ProtocolDiffStore."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """ServiceDiffFileStore implements ProtocolDiffStore interface."""
        store = ServiceDiffFileStore(base_path=tmp_path)
        assert isinstance(store, ProtocolDiffStore)

    def test_has_required_methods(self, store: ServiceDiffFileStore) -> None:
        """Store has all required protocol methods."""
        assert hasattr(store, "put")
        assert hasattr(store, "get")
        assert hasattr(store, "query")
        assert hasattr(store, "delete")
        assert hasattr(store, "exists")
        assert hasattr(store, "count")


# ============================================================================
# Test: Put and Get Operations
# ============================================================================


class TestStorePutAndGet:
    """Test cases for put and get operations."""

    async def test_put_and_get_from_buffer(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store correctly puts and gets diffs from buffer."""
        await store.put(sample_diff)

        retrieved = await store.get(sample_diff.diff_id)

        assert retrieved is not None
        assert retrieved.diff_id == sample_diff.diff_id
        assert retrieved.before_contract_name == sample_diff.before_contract_name

    async def test_put_and_get_from_file(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store correctly retrieves diffs from file after flush."""
        await store.put(sample_diff)
        await store.flush()

        retrieved = await store.get(sample_diff.diff_id)

        assert retrieved is not None
        assert retrieved.diff_id == sample_diff.diff_id

    async def test_get_nonexistent_returns_none(
        self, store: ServiceDiffFileStore
    ) -> None:
        """Store returns None for nonexistent diff ID."""
        nonexistent_id = uuid4()

        retrieved = await store.get(nonexistent_id)

        assert retrieved is None

    async def test_put_overwrites_existing(
        self, store: ServiceDiffFileStore, tmp_path: Path
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
        await store.flush()
        await store.put(diff_v2)

        retrieved = await store.get(diff_id)
        assert retrieved is not None
        assert retrieved.before_contract_name == "ContractB"


# ============================================================================
# Test: Flush Operations
# ============================================================================


class TestStoreFlush:
    """Test cases for flush operations."""

    async def test_flush_writes_to_file(
        self,
        store: ServiceDiffFileStore,
        sample_diff: ModelContractDiff,
        tmp_path: Path,
    ) -> None:
        """Store flush creates JSONL file with diffs."""
        await store.put(sample_diff)
        await store.flush()

        assert store.file_path.exists()
        content = store.file_path.read_text()
        assert len(content.strip().split("\n")) == 1

    async def test_flush_clears_buffer(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store flush clears the buffer."""
        await store.put(sample_diff)
        assert store.buffer_count == 1

        await store.flush()

        assert store.buffer_count == 0

    async def test_flush_empty_buffer_is_noop(
        self, store: ServiceDiffFileStore
    ) -> None:
        """Store flush with empty buffer does nothing."""
        await store.flush()

        assert not store.file_path.exists()

    async def test_auto_flush_when_buffer_full(
        self, store_small_buffer: ServiceDiffFileStore, tmp_path: Path
    ) -> None:
        """Store auto-flushes when buffer reaches buffer_size."""
        # Buffer size is 2, so after 2 puts should auto-flush
        diff1 = create_test_diff()
        diff2 = create_test_diff()
        diff3 = create_test_diff()

        await store_small_buffer.put(diff1)
        assert store_small_buffer.buffer_count == 1

        await store_small_buffer.put(diff2)
        # Should have auto-flushed
        assert store_small_buffer.buffer_count == 0

        await store_small_buffer.put(diff3)
        assert store_small_buffer.buffer_count == 1


# ============================================================================
# Test: Close Operations
# ============================================================================


class TestStoreClose:
    """Test cases for close operations."""

    async def test_close_flushes_buffer(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store close flushes remaining buffer."""
        await store.put(sample_diff)

        await store.close()

        assert store.file_path.exists()
        assert store.buffer_count == 0

    async def test_operations_after_close_raise_error(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store operations after close raise error."""
        await store.close()

        with pytest.raises(ModelOnexError):
            await store.put(sample_diff)

    async def test_is_ready_false_after_close(
        self, store: ServiceDiffFileStore
    ) -> None:
        """Store is_ready returns False after close."""
        assert store.is_ready is True

        await store.close()

        assert store.is_ready is False


# ============================================================================
# Test: Query Operations
# ============================================================================


class TestStoreQuery:
    """Test cases for query operations."""

    async def test_query_from_file(
        self, store: ServiceDiffFileStore, sample_diffs: list[ModelContractDiff]
    ) -> None:
        """Store query correctly retrieves from file."""
        for diff in sample_diffs:
            await store.put(diff)
        await store.flush()

        query = ModelDiffQuery()
        results = await store.query(query)

        assert len(results) == len(sample_diffs)

    async def test_query_combines_buffer_and_file(
        self, store: ServiceDiffFileStore
    ) -> None:
        """Store query combines buffer and file diffs."""
        diff1 = create_test_diff()
        diff2 = create_test_diff()

        await store.put(diff1)
        await store.flush()
        await store.put(diff2)

        query = ModelDiffQuery()
        results = await store.query(query)

        assert len(results) == 2

    async def test_query_deduplicates_by_id(self, store: ServiceDiffFileStore) -> None:
        """Store query deduplicates by diff_id (buffer takes precedence)."""
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
        await store.flush()
        # Put updated version in buffer (not flushed)
        store._buffer.append(diff_v2)

        query = ModelDiffQuery()
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].before_contract_name == "ContractB"

    async def test_query_empty_store(self, store: ServiceDiffFileStore) -> None:
        """Store query returns empty list for empty store."""
        query = ModelDiffQuery()
        results = await store.query(query)

        assert results == []


# ============================================================================
# Test: Delete Operations
# ============================================================================


class TestStoreDelete:
    """Test cases for delete operations."""

    async def test_delete_from_buffer(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store deletes diff from buffer."""
        await store.put(sample_diff)

        result = await store.delete(sample_diff.diff_id)

        assert result is True
        assert await store.get(sample_diff.diff_id) is None

    async def test_delete_from_file(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store deletes diff from file by rewriting."""
        await store.put(sample_diff)
        await store.flush()

        result = await store.delete(sample_diff.diff_id)

        assert result is True
        assert await store.get(sample_diff.diff_id) is None

    async def test_delete_nonexistent(self, store: ServiceDiffFileStore) -> None:
        """Store returns False when deleting nonexistent diff."""
        result = await store.delete(uuid4())

        assert result is False


# ============================================================================
# Test: Exists Operations
# ============================================================================


class TestStoreExists:
    """Test cases for exists operations."""

    async def test_exists_in_buffer(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store exists returns True for diff in buffer."""
        await store.put(sample_diff)

        result = await store.exists(sample_diff.diff_id)

        assert result is True

    async def test_exists_in_file(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store exists returns True for diff in file."""
        await store.put(sample_diff)
        await store.flush()

        result = await store.exists(sample_diff.diff_id)

        assert result is True

    async def test_exists_nonexistent(self, store: ServiceDiffFileStore) -> None:
        """Store exists returns False for nonexistent diff."""
        result = await store.exists(uuid4())

        assert result is False


# ============================================================================
# Test: Count Operations
# ============================================================================


class TestStoreCount:
    """Test cases for count operations."""

    async def test_count_combines_buffer_and_file(
        self, store: ServiceDiffFileStore
    ) -> None:
        """Store count includes both buffer and file diffs."""
        diff1 = create_test_diff()
        diff2 = create_test_diff()

        await store.put(diff1)
        await store.flush()
        await store.put(diff2)

        count = await store.count()

        assert count == 2

    async def test_count_deduplicates(self, store: ServiceDiffFileStore) -> None:
        """Store count deduplicates by diff_id."""
        diff_id = uuid4()

        diff = ModelContractDiff(
            diff_id=diff_id,
            before_contract_name="ContractA",
            after_contract_name="ContractA",
            field_diffs=[],
            list_diffs=[],
        )

        await store.put(diff)
        await store.flush()
        # Manually add same ID to buffer
        store._buffer.append(diff)

        count = await store.count()

        assert count == 1


# ============================================================================
# Test: Clear Operations
# ============================================================================


class TestStoreClear:
    """Test cases for clear operations."""

    async def test_clear_removes_buffer(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store clear removes buffer contents."""
        await store.put(sample_diff)

        await store.clear()

        assert store.buffer_count == 0

    async def test_clear_removes_file(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store clear removes storage file."""
        await store.put(sample_diff)
        await store.flush()
        assert store.file_path.exists()

        await store.clear()

        assert not store.file_path.exists()


# ============================================================================
# Test: Get All Operations
# ============================================================================


class TestStoreGetAll:
    """Test cases for get_all operations."""

    async def test_get_all_combines_buffer_and_file(
        self, store: ServiceDiffFileStore
    ) -> None:
        """Store get_all returns diffs from both buffer and file."""
        diff1 = create_test_diff()
        diff2 = create_test_diff()

        await store.put(diff1)
        await store.flush()
        await store.put(diff2)

        results = await store.get_all()

        assert len(results) == 2

    async def test_get_all_orders_by_computed_at(
        self, store: ServiceDiffFileStore
    ) -> None:
        """Store get_all orders by computed_at descending."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        old_diff = create_test_diff(computed_at=base_time - timedelta(hours=1))
        new_diff = create_test_diff(computed_at=base_time)

        await store.put(old_diff)
        await store.put(new_diff)
        await store.flush()

        results = await store.get_all()

        assert results[0].diff_id == new_diff.diff_id
        assert results[1].diff_id == old_diff.diff_id


# ============================================================================
# Test: File Path Properties
# ============================================================================


class TestStoreFilePath:
    """Test cases for file path properties."""

    def test_file_path_property(
        self, store: ServiceDiffFileStore, tmp_path: Path
    ) -> None:
        """Store file_path property returns correct path."""
        expected_path = tmp_path / "diffs.jsonl"
        assert store.file_path == expected_path

    def test_buffer_count_property(self, store: ServiceDiffFileStore) -> None:
        """Store buffer_count property returns correct count."""
        assert store.buffer_count == 0


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestStoreEdgeCases:
    """Test edge cases for the store."""

    async def test_handles_malformed_lines_in_file(
        self,
        store: ServiceDiffFileStore,
        sample_diff: ModelContractDiff,
        tmp_path: Path,
    ) -> None:
        """Store gracefully handles malformed lines in storage file."""
        # Create file with valid and invalid content
        await store.put(sample_diff)
        await store.flush()

        # Append malformed line to file
        with store.file_path.open("a") as f:
            f.write("this is not valid json\n")

        # Should still be able to query valid diffs
        results = await store.query(ModelDiffQuery())
        assert len(results) == 1

    async def test_handles_empty_lines_in_file(
        self, store: ServiceDiffFileStore, sample_diff: ModelContractDiff
    ) -> None:
        """Store gracefully handles empty lines in storage file."""
        await store.put(sample_diff)
        await store.flush()

        # Append empty lines
        with store.file_path.open("a") as f:
            f.write("\n\n\n")

        results = await store.query(ModelDiffQuery())
        assert len(results) == 1

    async def test_creates_directory_on_flush(self, tmp_path: Path) -> None:
        """Store creates directory on first flush if it doesn't exist."""
        nested_path = tmp_path / "nested" / "dirs"
        store = ServiceDiffFileStore(base_path=nested_path)

        diff = create_test_diff()
        await store.put(diff)
        await store.flush()

        assert nested_path.exists()
        assert store.file_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
