"""
Protocol definition for contract diff storage backends.

Defines the ProtocolDiffStore interface that all diff storage implementations
must satisfy. This enables pluggable backends (in-memory, PostgreSQL, etc.)
while maintaining a consistent API.

Example:
    >>> from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
    >>> from omnibase_core.services.diff.service_diff_in_memory_store import ServiceDiffInMemoryStore
    >>>
    >>> # ServiceDiffInMemoryStore implements ProtocolDiffStore
    >>> store: ProtocolDiffStore = ServiceDiffInMemoryStore()
    >>> # Now use store.put(), store.get(), store.query(), etc.

See Also:
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory implementation
    - :class:`~omnibase_core.models.contracts.diff.ModelContractDiff`:
      The diff model being stored
    - :class:`~omnibase_core.models.diff.model_diff_query.ModelDiffQuery`:
      Query filters for diff retrieval

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.contracts.diff import ModelContractDiff
    from omnibase_core.models.diff.model_diff_query import ModelDiffQuery


@runtime_checkable
class ProtocolDiffStore(Protocol):
    """
    Protocol defining the interface for contract diff storage backends.

    All diff storage implementations (in-memory, PostgreSQL, etc.) must
    implement this protocol to ensure consistent behavior across backends.

    The protocol defines six core operations:
        - ``put``: Store a diff (upsert semantics)
        - ``get``: Retrieve a diff by ID
        - ``query``: Search diffs with filters
        - ``delete``: Remove a diff by ID
        - ``exists``: Check if a diff exists
        - ``count``: Count diffs matching filters

    Thread Safety:
        Thread safety depends on the specific implementation. See individual
        implementation classes for their thread safety guarantees.

    Example:
        >>> class MyCustomStore:
        ...     async def put(self, diff: ModelContractDiff) -> None:
        ...         # Store diff in custom backend
        ...         pass
        ...
        ...     async def get(self, diff_id: UUID) -> ModelContractDiff | None:
        ...         # Retrieve diff from custom backend
        ...         return None
        ...
        ...     async def query(
        ...         self, filters: ModelDiffQuery
        ...     ) -> list[ModelContractDiff]:
        ...         # Query diffs with filters
        ...         return []
        ...
        ...     async def delete(self, diff_id: UUID) -> bool:
        ...         # Delete diff by ID
        ...         return False
        ...
        ...     async def exists(self, diff_id: UUID) -> bool:
        ...         # Check if diff exists
        ...         return False
        ...
        ...     async def count(self, filters: ModelDiffQuery | None = None) -> int:
        ...         # Count matching diffs
        ...         return 0

    .. versionadded:: 0.6.0
        Added as part of Diff Storage Infrastructure (OMN-1149)
    """

    async def put(self, diff: "ModelContractDiff") -> None:
        """
        Store a contract diff.

        Uses upsert semantics - if a diff with the same diff_id already exists,
        it will be overwritten.

        Args:
            diff: The contract diff to store.

        Raises:
            Implementation-specific exceptions may be raised for storage errors.

        Example:
            >>> from omnibase_core.models.contracts.diff import ModelContractDiff
            >>>
            >>> diff = ModelContractDiff(
            ...     before_contract_name="ContractA",
            ...     after_contract_name="ContractA",
            ... )
            >>> await store.put(diff)
        """
        ...

    async def get(self, diff_id: UUID) -> "ModelContractDiff | None":
        """
        Retrieve a diff by its unique identifier.

        Args:
            diff_id: The UUID of the diff to retrieve.

        Returns:
            The diff if found, None otherwise.

        Example:
            >>> diff = await store.get(diff_id)
            >>> if diff:
            ...     print(f"Found diff with {diff.total_changes} changes")
            ... else:
            ...     print("Diff not found")
        """
        ...

    async def query(self, filters: "ModelDiffQuery") -> "list[ModelContractDiff]":
        """
        Query diffs matching the specified filters.

        Filters are applied conjunctively (AND). Only diffs matching ALL
        specified filter criteria are returned.

        Args:
            filters: Query filters including contract names, time range,
                change types, limit, and offset for pagination.

        Returns:
            List of diffs matching all filter criteria, ordered by computed_at
            descending (newest first). The list length is bounded by filters.limit.

        Example:
            >>> from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
            >>>
            >>> query = ModelDiffQuery(
            ...     contract_name="MyContract",
            ...     has_changes=True,
            ...     limit=10,
            ... )
            >>> diffs = await store.query(query)
        """
        ...

    async def delete(self, diff_id: UUID) -> bool:
        """
        Delete a diff by its unique identifier.

        Args:
            diff_id: The UUID of the diff to delete.

        Returns:
            True if the diff was deleted, False if it was not found.

        Example:
            >>> deleted = await store.delete(diff_id)
            >>> if deleted:
            ...     print("Diff deleted successfully")
            ... else:
            ...     print("Diff not found")
        """
        ...

    async def exists(self, diff_id: UUID) -> bool:
        """
        Check if a diff exists in the store.

        Args:
            diff_id: The UUID of the diff to check.

        Returns:
            True if the diff exists, False otherwise.

        Example:
            >>> if await store.exists(diff_id):
            ...     diff = await store.get(diff_id)
        """
        ...

    async def count(self, filters: "ModelDiffQuery | None" = None) -> int:
        """
        Count diffs matching the specified filters.

        Args:
            filters: Optional query filters. If None, counts all diffs.
                The limit and offset fields in filters are ignored for counting.

        Returns:
            Number of diffs matching the filter criteria.

        Example:
            >>> # Count all diffs
            >>> total = await store.count()
            >>>
            >>> # Count diffs with changes
            >>> from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
            >>> query = ModelDiffQuery(has_changes=True)
            >>> with_changes = await store.count(query)
        """
        ...


__all__ = ["ProtocolDiffStore"]
