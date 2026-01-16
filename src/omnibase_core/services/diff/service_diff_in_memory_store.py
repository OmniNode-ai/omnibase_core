"""
In-memory implementation of ProtocolDiffStore.

Provides a simple dict-based storage backend for contract diffs. Suitable
for development, testing, and single-instance deployments. For production
multi-instance deployments, use a persistent backend like PostgreSQL.

Thread Safety:
    ServiceDiffInMemoryStore is NOT thread-safe. The internal dict is not protected
    by locks, and concurrent access from multiple threads may cause data
    corruption or race conditions.

    For thread-safe usage:
    - Use separate ServiceDiffInMemoryStore instances per thread, OR
    - Wrap all operations with threading.Lock

Example:
    >>> from omnibase_core.services.diff.service_diff_in_memory_store import ServiceDiffInMemoryStore
    >>> from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
    >>> from omnibase_core.models.contracts.diff import ModelContractDiff
    >>>
    >>> store = ServiceDiffInMemoryStore()
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

import threading
import warnings
from uuid import UUID

from omnibase_core.models.contracts.diff import ModelContractDiff
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.models.diff.model_diff_storage_configuration import (
    ModelDiffStorageConfiguration,
)
from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore


class ServiceDiffInMemoryStore:
    """
    In-memory diff storage implementation.

    Stores diffs in a Python dict keyed by diff_id. Implements all
    ProtocolDiffStore methods for filtering, pagination, and counting.

    Attributes:
        _diffs: Internal dict mapping diff_id to ModelContractDiff.
        _config: Storage configuration.
        _owner_thread: Thread ID that created/first accessed the store.
        _thread_check_enabled: Whether thread safety checks are enabled.

    Thread Safety:
        NOT thread-safe. See module docstring for details.

        Runtime Detection:
            This class includes runtime detection for cross-thread access.
            When a mutating method (put, delete, clear) is called from a
            different thread than the one that first accessed the store,
            a RuntimeWarning is emitted. This helps catch accidental
            thread-safety violations during development.

            To disable thread safety warnings (e.g., for testing):
                store._thread_check_enabled = False

    Memory Considerations:
        All diffs are stored in memory. For long-running applications with
        many diffs, consider:
        - Implementing a TTL-based eviction policy
        - Using a bounded dict with LRU eviction
        - Switching to a persistent backend

    Performance Characteristics:
        - put(): O(1)
        - get(): O(1)
        - delete(): O(1)
        - exists(): O(1)
        - query(): O(n) filter + O(n log n) sort where n = total diffs
        - count(): O(n) filter
        - clear(): O(1)
        - get_all(): O(n log n) sort

        This backend is suitable for <10,000 diffs. For larger datasets,
        consider using a persistent backend with indexed queries.

    Example:
        >>> store = ServiceDiffInMemoryStore()
        >>> await store.put(diff)
        >>> print(f"Stored {len(store)} diffs")

    .. versionadded:: 0.6.0
        Added as part of Diff Storage Infrastructure (OMN-1149)
    """

    _owner_thread: int | None
    _thread_check_enabled: bool

    def __init__(self, config: ModelDiffStorageConfiguration | None = None) -> None:
        """
        Initialize an empty in-memory diff store.

        Args:
            config: Optional storage configuration. If not provided, uses
                default configuration.
        """
        self._diffs: dict[UUID, ModelContractDiff] = {}
        self._config = config or ModelDiffStorageConfiguration()
        self._owner_thread: int | None = None
        self._thread_check_enabled = True  # Can be disabled for testing

    def __len__(self) -> int:
        """Return the number of diffs in the store."""
        return len(self._diffs)

    @property
    def config(self) -> ModelDiffStorageConfiguration:
        """Get the storage configuration."""
        return self._config

    def _check_thread_safety(self) -> None:
        """
        Check if the store is being accessed from the same thread.

        On first call, records the current thread ID as the owner.
        On subsequent calls, emits a RuntimeWarning if the current
        thread differs from the owner thread.

        This method is called at the start of mutating operations
        (put, delete, clear) to detect accidental cross-thread access.
        """
        if not self._thread_check_enabled:
            return

        current_thread = threading.current_thread().ident
        if self._owner_thread is None:
            self._owner_thread = current_thread
        elif current_thread != self._owner_thread:
            warnings.warn(
                f"ServiceDiffInMemoryStore accessed from thread {current_thread} but was created "
                f"in thread {self._owner_thread}. ServiceDiffInMemoryStore is NOT thread-safe. "
                f"Use separate instances per thread or wrap with threading.Lock.",
                RuntimeWarning,
                stacklevel=3,
            )

    async def put(self, diff: ModelContractDiff) -> None:
        """
        Store a contract diff.

        Uses upsert semantics - if a diff with the same diff_id exists,
        it will be overwritten.

        Args:
            diff: The contract diff to store.

        Warning:
            Emits RuntimeWarning if called from a different thread than
            the one that first accessed this store instance.
        """
        self._check_thread_safety()
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

        Performance:
            O(n) filter + O(n log n) sort. For large datasets (>10,000 diffs),
            consider using ServiceDiffFileStore or a database-backed store.
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

        Warning:
            Emits RuntimeWarning if called from a different thread than
            the one that first accessed this store instance.
        """
        self._check_thread_safety()
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

        Performance:
            O(n) filter where n = total diffs stored.
        """
        if filters is None:
            return len(self._diffs)

        # Apply filters (ignore pagination)
        return sum(1 for diff in self._diffs.values() if filters.matches_diff(diff))

    async def clear(self) -> None:
        """
        Remove all diffs from the store.

        Useful for testing and cleanup.

        Warning:
            Emits RuntimeWarning if called from a different thread than
            the one that first accessed this store instance.
        """
        self._check_thread_safety()
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
_store_check: ProtocolDiffStore = ServiceDiffInMemoryStore()

__all__ = ["ServiceDiffInMemoryStore"]
