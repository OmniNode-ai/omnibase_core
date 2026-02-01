"""
High-level service for managing contract diff history.

ServiceDiffHistory provides a convenient API for storing, querying, and rendering
diffs. It wraps a ProtocolDiffStore implementation for actual storage, enabling
pluggable backends while providing high-level convenience methods.

Thread Safety:
    Thread safety depends on the underlying ProtocolDiffStore implementation.
    When using ServiceDiffInMemoryStore, the service is NOT thread-safe.
    See ServiceDiffInMemoryStore documentation for thread safety guidelines.

Example:
    >>> from omnibase_core.services.diff.service_diff_history import (
    ...     ServiceDiffHistory,
    ... )
    >>> from omnibase_core.services.diff.service_diff_in_memory_store import ServiceDiffInMemoryStore
    >>> from omnibase_core.models.contracts.diff import ModelContractDiff
    >>> from omnibase_core.enums.enum_output_format import EnumOutputFormat
    >>>
    >>> # Create service with in-memory backend
    >>> store = ServiceDiffInMemoryStore()
    >>> service = ServiceDiffHistory(store)
    >>>
    >>> # Record a diff
    >>> diff = ModelContractDiff(
    ...     before_contract_name="ContractA",
    ...     after_contract_name="ContractA",
    ... )
    >>> diff_id = await service.record_diff(diff)
    >>>
    >>> # Retrieve and render the diff
    >>> rendered = await service.render_diff(diff_id, EnumOutputFormat.MARKDOWN)

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_diff_store.ProtocolDiffStore`:
      The storage backend protocol
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory backend implementation
    - :class:`~omnibase_core.rendering.renderer_diff.RendererDiff`:
      Multi-format diff renderer

.. versionadded:: 0.6.0
    Added as part of Explainability Output: Diff Rendering + Storage Hooks (OMN-1149)
"""

from datetime import datetime, timedelta
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_output_format import EnumOutputFormat
from omnibase_core.models.contracts.diff import ModelContractDiff
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
from omnibase_core.rendering.renderer_diff import RendererDiff


class ServiceDiffHistory:
    """
    High-level service for managing contract diff history.

    Provides convenient APIs for storing, querying, and rendering diffs.
    Wraps a ProtocolDiffStore implementation for actual storage.

    Attributes:
        _store: The underlying diff storage backend.

    Thread Safety:
        Thread safety is determined by the underlying store implementation.
        See store-specific documentation for details.

    Example:
        >>> from omnibase_core.services.diff.service_diff_history import (
        ...     ServiceDiffHistory,
        ... )
        >>> from omnibase_core.services.diff.service_diff_in_memory_store import ServiceDiffInMemoryStore
        >>>
        >>> store = ServiceDiffInMemoryStore()
        >>> service = ServiceDiffHistory(store)
        >>>
        >>> # Record diffs
        >>> diff_id = await service.record_diff(diff)
        >>>
        >>> # Query diffs
        >>> recent = await service.get_recent_diffs(limit=10)
        >>>
        >>> # Get statistics
        >>> stats = await service.get_change_statistics(contract_name="MyContract")

    .. versionadded:: 0.6.0
        Added as part of Explainability Output (OMN-1149)
    """

    def __init__(self, store: ProtocolDiffStore) -> None:
        """
        Initialize with a storage backend.

        Args:
            store: Storage backend implementing ProtocolDiffStore.
                The service delegates all storage operations to this backend.

        Example:
            >>> from omnibase_core.services.diff.service_diff_in_memory_store import (
            ...     ServiceDiffInMemoryStore,
            ... )
            >>> store = ServiceDiffInMemoryStore()
            >>> service = ServiceDiffHistory(store)
        """
        self._store = store

    # =========================================================================
    # Core CRUD Operations
    # =========================================================================

    async def record_diff(self, diff: ModelContractDiff) -> UUID:
        """
        Store a diff and return its ID.

        Uses upsert semantics - if a diff with the same diff_id already exists,
        it will be overwritten.

        Args:
            diff: The contract diff to store.

        Returns:
            The diff_id of the recorded diff.

        Example:
            >>> from omnibase_core.models.contracts.diff import ModelContractDiff
            >>>
            >>> diff = ModelContractDiff(
            ...     before_contract_name="MyContract",
            ...     after_contract_name="MyContract",
            ... )
            >>> diff_id = await service.record_diff(diff)
            >>> print(f"Recorded diff: {diff_id}")
        """
        await self._store.put(diff)
        return diff.diff_id

    async def get_diff(self, diff_id: UUID) -> ModelContractDiff | None:
        """
        Retrieve a diff by ID.

        Args:
            diff_id: The UUID of the diff to retrieve.

        Returns:
            The diff if found, None otherwise.

        Example:
            >>> diff = await service.get_diff(diff_id)
            >>> if diff:
            ...     print(f"Diff has {diff.total_changes} changes")
            ... else:
            ...     print("Diff not found")
        """
        return await self._store.get(diff_id)

    async def delete_diff(self, diff_id: UUID) -> bool:
        """
        Delete a diff by ID.

        Args:
            diff_id: The UUID of the diff to delete.

        Returns:
            True if the diff was deleted, False if it was not found.

        Example:
            >>> deleted = await service.delete_diff(diff_id)
            >>> if deleted:
            ...     print("Diff deleted successfully")
            ... else:
            ...     print("Diff not found")
        """
        return await self._store.delete(diff_id)

    # =========================================================================
    # Query Convenience Methods
    # =========================================================================

    async def query_diffs(self, query: ModelDiffQuery) -> list[ModelContractDiff]:
        """
        Query diffs with filters.

        Filters are applied conjunctively (AND). Only diffs matching ALL
        specified filter criteria are returned.

        Args:
            query: Query filters including contract names, time range,
                change types, limit, and offset for pagination.

        Returns:
            List of diffs matching all filter criteria, ordered by computed_at
            descending (newest first).

        Example:
            >>> from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
            >>>
            >>> query = ModelDiffQuery(
            ...     contract_name="MyContract",
            ...     has_changes=True,
            ...     limit=20,
            ... )
            >>> diffs = await service.query_diffs(query)
            >>> print(f"Found {len(diffs)} diffs")
        """
        return await self._store.query(query)

    async def get_recent_diffs(
        self,
        limit: int = 10,
        contract_name: str | None = None,
    ) -> list[ModelContractDiff]:
        """
        Get most recent diffs, optionally filtered by contract name.

        Convenience method for retrieving the latest diffs without
        constructing a full ModelDiffQuery.

        Args:
            limit: Maximum number of diffs to return (default 10).
            contract_name: Optional filter by contract name. If provided,
                matches diffs where either before or after contract name
                equals this value.

        Returns:
            List of diffs ordered by computed_at descending (newest first).

        Example:
            >>> # Get 10 most recent diffs
            >>> recent = await service.get_recent_diffs()
            >>>
            >>> # Get recent diffs for a specific contract
            >>> recent = await service.get_recent_diffs(
            ...     limit=5, contract_name="MyContract"
            ... )
        """
        query = ModelDiffQuery(
            contract_name=contract_name,
            limit=limit,
        )
        return await self._store.query(query)

    async def get_diffs_in_range(
        self,
        start: datetime,
        end: datetime,
        contract_name: str | None = None,
    ) -> list[ModelContractDiff]:
        """
        Get diffs within a time range.

        Args:
            start: Start of the time range (inclusive).
            end: End of the time range (exclusive).
            contract_name: Optional filter by contract name.

        Returns:
            List of diffs computed within the specified time range,
            ordered by computed_at descending (newest first).

        Raises:
            ModelOnexError: If end is before start (with VALIDATION_ERROR code).

        Example:
            >>> from datetime import datetime, UTC, timedelta
            >>>
            >>> now = datetime.now(UTC)
            >>> diffs = await service.get_diffs_in_range(
            ...     start=now - timedelta(hours=24),
            ...     end=now,
            ... )
            >>> print(f"Found {len(diffs)} diffs in last 24 hours")
        """
        if end < start:
            raise ModelOnexError(
                message=f"end ({end}) cannot be before start ({start})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        query = ModelDiffQuery(
            contract_name=contract_name,
            computed_after=start,
            computed_before=end,
            limit=1000,  # High limit to get all in range
        )
        return await self._store.query(query)

    async def get_contract_history(
        self,
        contract_name: str,
        limit: int = 50,
    ) -> list[ModelContractDiff]:
        """
        Get diff history for a specific contract.

        Retrieves the change history for a contract, ordered from most
        recent to oldest.

        Args:
            contract_name: The contract name to filter by.
            limit: Maximum number of diffs to return (default 50).

        Returns:
            List of diffs for the specified contract, ordered by
            computed_at descending (newest first).

        Example:
            >>> history = await service.get_contract_history("MyContract")
            >>> for diff in history:
            ...     print(f"{diff.computed_at}: {diff.total_changes} changes")
        """
        query = ModelDiffQuery(
            contract_name=contract_name,
            limit=limit,
        )
        return await self._store.query(query)

    # =========================================================================
    # Statistics and Aggregation
    # =========================================================================

    async def get_diff_count(
        self,
        contract_name: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """
        Count diffs, optionally filtered.

        Args:
            contract_name: Optional filter by contract name.
            since: Optional filter for diffs computed at or after this time.

        Returns:
            Number of diffs matching the filter criteria.

        Example:
            >>> # Count all diffs
            >>> total = await service.get_diff_count()
            >>>
            >>> # Count diffs for a specific contract since a time
            >>> from datetime import datetime, UTC, timedelta
            >>> count = await service.get_diff_count(
            ...     contract_name="MyContract",
            ...     since=datetime.now(UTC) - timedelta(days=7),
            ... )
        """
        query = ModelDiffQuery(
            contract_name=contract_name,
            computed_after=since,
        )
        return await self._store.count(query)

    async def get_change_statistics(
        self,
        contract_name: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, int]:
        """
        Get aggregated change statistics.

        Aggregates statistics across all matching diffs, providing totals
        for each change type.

        Args:
            contract_name: Optional filter by contract name.
            since: Optional filter for diffs computed at or after this time.

        Returns:
            Dictionary with keys: 'total_diffs', 'total_changes',
            'added', 'removed', 'modified', 'moved'.

        Example:
            >>> stats = await service.get_change_statistics(
            ...     contract_name="MyContract",
            ... )
            >>> print(f"Total diffs: {stats['total_diffs']}")
            >>> print(f"Total changes: {stats['total_changes']}")
            >>> print(f"Added: {stats['added']}, Removed: {stats['removed']}")
        """
        query = ModelDiffQuery(
            contract_name=contract_name,
            computed_after=since,
            limit=1000,  # High limit to get all matching
        )
        diffs = await self._store.query(query)

        # Initialize aggregated statistics
        stats: dict[str, int] = {
            "total_diffs": len(diffs),
            "total_changes": 0,
            "added": 0,
            "removed": 0,
            "modified": 0,
            "moved": 0,
        }

        # Aggregate from each diff's change_summary
        for diff in diffs:
            stats["total_changes"] += diff.total_changes
            summary = diff.change_summary
            stats["added"] += summary["added"]
            stats["removed"] += summary["removed"]
            stats["modified"] += summary["modified"]
            stats["moved"] += summary["moved"]

        return stats

    # =========================================================================
    # Rendering Convenience Methods
    # =========================================================================

    async def render_diff(
        self,
        diff_id: UUID,
        output_format: EnumOutputFormat = EnumOutputFormat.TEXT,
    ) -> str | None:
        """
        Retrieve and render a diff.

        Combines retrieval and rendering in a single operation for
        convenience.

        Args:
            diff_id: The UUID of the diff to retrieve and render.
            output_format: The output format to use (default TEXT).

        Returns:
            Rendered diff string if found, None if diff not found.

        Example:
            >>> from omnibase_core.enums.enum_output_format import EnumOutputFormat
            >>>
            >>> # Render as markdown for documentation
            >>> md = await service.render_diff(diff_id, EnumOutputFormat.MARKDOWN)
            >>> if md:
            ...     print(md)
            ... else:
            ...     print("Diff not found")
        """
        diff = await self._store.get(diff_id)
        if diff is None:
            return None
        return RendererDiff.render(diff, output_format)

    async def render_recent_diffs(
        self,
        limit: int = 5,
        output_format: EnumOutputFormat = EnumOutputFormat.TEXT,
        contract_name: str | None = None,
    ) -> str:
        """
        Render recent diffs as a combined report.

        Retrieves and renders multiple recent diffs, combining them into
        a single formatted output with separators between diffs.

        Args:
            limit: Maximum number of diffs to include (default 5).
            output_format: The output format to use (default TEXT).
            contract_name: Optional filter by contract name.

        Returns:
            Combined rendered output of all recent diffs. Returns
            "No diffs found." if no diffs match the criteria.

        Example:
            >>> # Render recent diffs as markdown
            >>> report = await service.render_recent_diffs(
            ...     limit=3,
            ...     output_format=EnumOutputFormat.MARKDOWN,
            ...     contract_name="MyContract",
            ... )
            >>> print(report)
        """
        diffs = await self.get_recent_diffs(limit=limit, contract_name=contract_name)

        if not diffs:
            return "No diffs found."

        rendered_parts: list[str] = []
        for i, diff in enumerate(diffs):
            rendered = RendererDiff.render(diff, output_format)
            rendered_parts.append(rendered)

            # Add separator between diffs (except after last)
            if i < len(diffs) - 1:
                if output_format == EnumOutputFormat.MARKDOWN:
                    rendered_parts.append("\n---\n")
                elif output_format == EnumOutputFormat.JSON:
                    # For JSON, we'll separate with commas
                    # But wrap in array format
                    pass
                else:
                    rendered_parts.append("\n" + "=" * 60 + "\n")

        # For JSON format, wrap multiple diffs in an array
        if output_format == EnumOutputFormat.JSON and len(diffs) > 1:
            # Combine JSON objects into array
            import json

            json_objects = []
            for diff in diffs:
                json_objects.append(diff.model_dump(mode="json"))
            return json.dumps(json_objects, indent=2, ensure_ascii=False)

        return "\n".join(rendered_parts)

    # =========================================================================
    # Cleanup Operations
    # =========================================================================

    async def cleanup_old_diffs(
        self,
        older_than: datetime | timedelta,
    ) -> int:
        """
        Delete diffs older than specified time.

        Useful for maintenance and preventing unbounded storage growth.

        Args:
            older_than: Either a datetime (delete before this time) or
                a timedelta (delete older than this duration from now).

        Returns:
            Count of diffs deleted.

        Example:
            >>> from datetime import timedelta
            >>>
            >>> # Delete diffs older than 30 days
            >>> deleted = await service.cleanup_old_diffs(timedelta(days=30))
            >>> print(f"Deleted {deleted} old diffs")
            >>>
            >>> # Delete diffs before a specific date
            >>> from datetime import datetime, UTC
            >>> cutoff = datetime(2024, 1, 1, tzinfo=UTC)
            >>> deleted = await service.cleanup_old_diffs(cutoff)
        """
        # Convert timedelta to datetime if needed
        if isinstance(older_than, timedelta):
            from datetime import UTC

            cutoff = datetime.now(UTC) - older_than
        else:
            cutoff = older_than

        # Query all diffs before the cutoff
        query = ModelDiffQuery(
            computed_before=cutoff,
            limit=1000,  # Process in batches
        )
        old_diffs = await self._store.query(query)

        # Delete each old diff
        deleted_count = 0
        for diff in old_diffs:
            if await self._store.delete(diff.diff_id):
                deleted_count += 1

        return deleted_count


__all__ = ["ServiceDiffHistory"]
