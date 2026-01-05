# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
In-memory implementation of ProtocolDiffStore.

Provides a simple dict-based storage backend for contract diffs. Suitable
for development, testing, and single-instance deployments. For production
multi-instance deployments, use a persistent backend like PostgreSQL.

Thread Safety:
    StoreDiffInMemory is NOT thread-safe. The internal dict is not protected
    by locks, and concurrent access from multiple threads may cause data
    corruption or race conditions.

    For thread-safe usage:
    - Use separate StoreDiffInMemory instances per thread, OR
    - Wrap all operations with threading.Lock

Example:
    >>> from omnibase_core.services.diff.store_diff_in_memory import StoreDiffInMemory
    >>> from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
    >>> from omnibase_core.models.contracts.diff import ModelContractDiff
    >>>
    >>> store = StoreDiffInMemory()
    >>>
    >>> # Store a diff
    >>> diff = ModelContractDiff(
    ...     before_contract_name="ContractA",
    ...     after_contract_name="ContractA",
    ... )
    >>> await store.put(diff)
    >>>
    >>> # Retrieve by ID
    >>> retrieved = await store.get(diff.diff_id)
    >>> assert retrieved == diff

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_diff_store.ProtocolDiffStore`:
      The protocol this class implements
    - :class:`~omnibase_core.models.diff.model_diff_storage_configuration.ModelDiffStorageConfiguration`:
      Configuration model for storage backends

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from uuid import UUID

from omnibase_core.models.contracts.diff import ModelContractDiff
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.models.diff.model_diff_storage_configuration import (
    ModelDiffStorageConfiguration,
)
from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore


class StoreDiffInMemory:
    """
    In-memory diff storage implementation.

    Stores diffs in a Python dict keyed by diff_id. Implements all
    ProtocolDiffStore methods for filtering, pagination, and counting.

    Attributes:
        _diffs: Internal dict mapping diff_id to ModelContractDiff.
        _config: Storage configuration.

    Thread Safety:
        NOT thread-safe. See module docstring for details.

    Memory Considerations:
        All diffs are stored in memory. For long-running applications with
        many diffs, consider:
        - Implementing a TTL-based eviction policy
        - Using a bounded dict with LRU eviction
        - Switching to a persistent backend

    Example:
        >>> store = StoreDiffInMemory()
        >>> await store.put(diff)
        >>> print(f"Stored {len(store)} diffs")

    .. versionadded:: 0.6.0
        Added as part of Diff Storage Infrastructure (OMN-1149)
    """

    def __init__(self, config: ModelDiffStorageConfiguration | None = None) -> None:
        """
        Initialize an empty in-memory diff store.

        Args:
            config: Optional storage configuration. If not provided, uses
                default configuration.
        """
        self._diffs: dict[UUID, ModelContractDiff] = {}
        self._config = config or ModelDiffStorageConfiguration()

    def __len__(self) -> int:
        """Return the number of diffs in the store."""
        return len(self._diffs)

    @property
    def config(self) -> ModelDiffStorageConfiguration:
        """Get the storage configuration."""
        return self._config

    async def put(self, diff: ModelContractDiff) -> None:
        """
        Store a contract diff.

        Uses upsert semantics - if a diff with the same diff_id exists,
        it will be overwritten.

        Args:
            diff: The contract diff to store.
        """
        self._diffs[diff.diff_id] = diff

    async def get(self, diff_id: UUID) -> ModelContractDiff | None:
        """
        Retrieve a diff by its unique identifier.

        Args:
            diff_id: The UUID of the diff to retrieve.

        Returns:
            The diff if found, None otherwise.
        """
        return self._diffs.get(diff_id)

    async def query(self, filters: ModelDiffQuery) -> list[ModelContractDiff]:
        """
        Query diffs matching the specified filters.

        Filters are applied conjunctively (AND). Results are ordered by
        computed_at descending (newest first) and bounded by limit/offset.

        Args:
            filters: Query filters including contract names, time range,
                change types, limit, and offset for pagination.

        Returns:
            List of matching diffs, ordered by computed_at descending.
        """
        # Apply filters
        matching_diffs = [
            diff for diff in self._diffs.values() if filters.matches_diff(diff)
        ]

        # Sort by computed_at descending (newest first)
        matching_diffs.sort(key=lambda d: d.computed_at, reverse=True)

        # Apply pagination
        start_idx = filters.offset
        end_idx = start_idx + filters.limit
        return matching_diffs[start_idx:end_idx]

    async def delete(self, diff_id: UUID) -> bool:
        """
        Delete a diff by its unique identifier.

        Args:
            diff_id: The UUID of the diff to delete.

        Returns:
            True if the diff was deleted, False if it was not found.
        """
        if diff_id in self._diffs:
            del self._diffs[diff_id]
            return True
        return False

    async def exists(self, diff_id: UUID) -> bool:
        """
        Check if a diff exists in the store.

        Args:
            diff_id: The UUID of the diff to check.

        Returns:
            True if the diff exists, False otherwise.
        """
        return diff_id in self._diffs

    async def count(self, filters: ModelDiffQuery | None = None) -> int:
        """
        Count diffs matching the specified filters.

        Args:
            filters: Optional query filters. If None, counts all diffs.
                The limit and offset fields in filters are ignored for counting.

        Returns:
            Number of diffs matching the filter criteria.
        """
        if filters is None:
            return len(self._diffs)

        # Apply filters (ignore pagination)
        return sum(1 for diff in self._diffs.values() if filters.matches_diff(diff))

    async def clear(self) -> None:
        """
        Remove all diffs from the store.

        Useful for testing and cleanup.
        """
        self._diffs.clear()

    async def get_all(self) -> list[ModelContractDiff]:
        """
        Get all diffs in the store.

        Returns:
            List of all stored diffs, ordered by computed_at descending.
        """
        diffs = list(self._diffs.values())
        diffs.sort(key=lambda d: d.computed_at, reverse=True)
        return diffs


# Verify protocol compliance at module load time
_store_check: ProtocolDiffStore = StoreDiffInMemory()

__all__ = ["StoreDiffInMemory"]
