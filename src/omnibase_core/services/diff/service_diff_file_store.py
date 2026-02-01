"""
File-based implementation of ProtocolDiffStore.

Provides a JSONL-based storage backend for contract diffs. Suitable for
development, testing, and single-instance deployments where persistence
is needed but a full database is not required.

Storage Format:
    Uses JSONL (JSON Lines) format where each line is a complete JSON object
    representing a single ModelContractDiff. This format supports:
    - Efficient append operations
    - Easy line-by-line parsing
    - Human-readable storage

Thread Safety:
    ServiceDiffFileStore is NOT thread-safe. The internal buffer and file operations
    are not protected by locks, and concurrent access from multiple threads
    may cause data corruption or race conditions.

    For thread-safe usage:
    - Use separate ServiceDiffFileStore instances per thread, OR
    - Wrap all operations with threading.Lock

Example:
    >>> from pathlib import Path
    >>> from omnibase_core.services.diff.service_diff_file_store import ServiceDiffFileStore
    >>> from omnibase_core.models.contracts.diff import ModelContractDiff
    >>>
    >>> store = ServiceDiffFileStore(base_path=Path("/tmp/diffs"))
    >>>
    >>> # Store a diff
    >>> diff = ModelContractDiff(
    ...     before_contract_name="ContractA",
    ...     after_contract_name="ContractA",
    ... )
    >>> await store.put(diff)
    >>>
    >>> # Flush buffered writes
    >>> await store.flush()
    >>>
    >>> # Retrieve by ID
    >>> retrieved = await store.get(diff.diff_id)
    >>> assert retrieved == diff
    >>>
    >>> # Close when done
    >>> await store.close()

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_diff_store.ProtocolDiffStore`:
      The protocol this class implements
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory implementation for comparison
    - :class:`~omnibase_core.services.sinks.service_sink_file.ServiceFileSink`:
      Similar pattern for event sinks

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

import json
from pathlib import Path
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.contracts.diff import ModelContractDiff
from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.models.diff.model_diff_storage_configuration import (
    ModelDiffStorageConfiguration,
)
from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore


class ServiceDiffFileStore:
    """
    File-based diff storage using JSONL format.

    Stores diffs in a JSONL file (one JSON object per line) with buffered
    writes for efficiency. Implements all ProtocolDiffStore methods for
    filtering, pagination, and counting.

    Storage structure:
        {base_path}/
            diffs.jsonl          # Main storage file

    Attributes:
        _base_path: Directory for storing diff files.
        _config: Storage configuration.
        _buffer_size: Number of diffs to buffer before auto-flush.
        _buffer: Internal buffer for pending writes.

    Thread Safety:
        NOT thread-safe. See module docstring for details.

    Performance Considerations:
        - Uses load-then-filter for queries (simple but not optimal for large files)
        - Buffered writes reduce I/O overhead
        - Consider ServiceDiffInMemoryStore or PostgreSQL backend for high-volume usage

    Example:
        >>> store = ServiceDiffFileStore(base_path=Path("/tmp/diffs"))
        >>> await store.put(diff)
        >>> await store.flush()
        >>> print(f"Stored diff, buffer has {store.buffer_count} pending writes")

    .. versionadded:: 0.6.0
        Added as part of Diff Storage Infrastructure (OMN-1149)
    """

    # Default filename for the JSONL storage file
    STORAGE_FILENAME = "diffs.jsonl"

    def __init__(
        self,
        base_path: Path,
        config: ModelDiffStorageConfiguration | None = None,
        buffer_size: int = 10,
    ) -> None:
        """
        Initialize file-based storage.

        Args:
            base_path: Directory for storing diff files. Will be created
                if it doesn't exist on first write.
            config: Optional storage configuration. If not provided, uses
                default configuration.
            buffer_size: Number of diffs to buffer before auto-flush.
                Defaults to 10. Set to 1 for immediate writes.
        """
        self._base_path = base_path
        self._config = config or ModelDiffStorageConfiguration()
        self._buffer_size = buffer_size
        self._buffer: list[ModelContractDiff] = []
        self._ready = True

    @property
    def file_path(self) -> Path:
        """Get the path to the JSONL storage file."""
        return self._base_path / self.STORAGE_FILENAME

    @property
    def config(self) -> ModelDiffStorageConfiguration:
        """Get the storage configuration."""
        return self._config

    @property
    def buffer_count(self) -> int:
        """Return the number of diffs in the buffer."""
        return len(self._buffer)

    @property
    def is_ready(self) -> bool:
        """Check if the store is ready for operations."""
        return self._ready

    async def put(self, diff: ModelContractDiff) -> None:
        """
        Store a contract diff.

        Buffers the diff and flushes when buffer is full. Uses upsert
        semantics - if a diff with the same diff_id exists, the file
        will be rewritten with the new version.

        Args:
            diff: The contract diff to store.

        Raises:
            ModelOnexError: If the store is closed or write fails.
        """
        if not self._ready:
            raise ModelOnexError(
                message=f"File store at '{self._base_path}' is closed",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={"path": str(self._base_path)},
            )

        # Check if diff with same ID exists (upsert semantics)
        existing = await self.get(diff.diff_id)
        if existing is not None:
            # Remove from existing file by rewriting without this ID
            await self._rewrite_without(diff.diff_id)

        # Add to buffer
        self._buffer.append(diff)

        # Auto-flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            await self.flush()

    async def get(self, diff_id: UUID) -> ModelContractDiff | None:
        """
        Retrieve a diff by its unique identifier.

        Checks buffer first, then loads from file.

        Args:
            diff_id: The UUID of the diff to retrieve.

        Returns:
            The diff if found, None otherwise.
        """
        # Check buffer first
        for diff in self._buffer:
            if diff.diff_id == diff_id:
                return diff

        # Load from file
        all_diffs = await self._load_all()
        for diff in all_diffs:
            if diff.diff_id == diff_id:
                return diff

        return None

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
        # Combine buffer and file diffs
        all_diffs = await self._load_all()
        all_diffs.extend(self._buffer)

        # Deduplicate by diff_id (buffer takes precedence)
        seen_ids: set[UUID] = set()
        unique_diffs: list[ModelContractDiff] = []

        # Process buffer first (more recent)
        for diff in self._buffer:
            if diff.diff_id not in seen_ids:
                seen_ids.add(diff.diff_id)
                unique_diffs.append(diff)

        # Then file diffs
        for diff in await self._load_all():
            if diff.diff_id not in seen_ids:
                seen_ids.add(diff.diff_id)
                unique_diffs.append(diff)

        # Apply filters
        matching_diffs = [diff for diff in unique_diffs if filters.matches_diff(diff)]

        # Sort by computed_at descending (newest first)
        matching_diffs.sort(key=lambda d: d.computed_at, reverse=True)

        # Apply pagination
        start_idx = filters.offset
        end_idx = start_idx + filters.limit
        return matching_diffs[start_idx:end_idx]

    async def delete(self, diff_id: UUID) -> bool:
        """
        Delete a diff by its unique identifier.

        Removes from buffer if present, then rewrites file without the diff.

        Args:
            diff_id: The UUID of the diff to delete.

        Returns:
            True if the diff was deleted, False if it was not found.
        """
        found = False

        # Check buffer
        for i, diff in enumerate(self._buffer):
            if diff.diff_id == diff_id:
                del self._buffer[i]
                found = True
                break

        # Check file and rewrite if needed
        if await self._exists_in_file(diff_id):
            await self._rewrite_without(diff_id)
            found = True

        return found

    async def exists(self, diff_id: UUID) -> bool:
        """
        Check if a diff exists in the store.

        Args:
            diff_id: The UUID of the diff to check.

        Returns:
            True if the diff exists, False otherwise.
        """
        # Check buffer
        for diff in self._buffer:
            if diff.diff_id == diff_id:
                return True

        # Check file
        return await self._exists_in_file(diff_id)

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
            # Count all unique diffs
            all_diffs = await self._load_all()
            all_ids = {diff.diff_id for diff in all_diffs}
            buffer_ids = {diff.diff_id for diff in self._buffer}
            return len(all_ids | buffer_ids)

        # Apply filters (ignore pagination)
        all_diffs = await self._load_all()
        all_diffs.extend(self._buffer)

        # Deduplicate
        seen_ids: set[UUID] = set()
        count = 0
        for diff in all_diffs:
            if diff.diff_id not in seen_ids:
                seen_ids.add(diff.diff_id)
                if filters.matches_diff(diff):
                    count += 1

        return count

    async def flush(self) -> None:
        """
        Flush buffered diffs to file.

        Writes all buffered diffs to the JSONL file and clears the buffer.
        Creates the storage directory if it doesn't exist.

        Raises:
            ModelOnexError: If writing to file fails.
        """
        if not self._buffer:
            return

        try:
            # Ensure parent directory exists
            self._base_path.mkdir(parents=True, exist_ok=True)

            # Append buffered diffs to file
            with self.file_path.open("a", encoding="utf-8") as f:
                for diff in self._buffer:
                    json_line = self._serialize_diff(diff)
                    f.write(json_line + "\n")

            self._buffer.clear()

        except OSError as e:
            raise ModelOnexError(
                message=f"Failed to write diffs to file: {e}",
                error_code=EnumCoreErrorCode.FILE_WRITE_ERROR,
                context={
                    "path": str(self._base_path),
                    "buffer_count": len(self._buffer),
                },
            ) from e

    async def close(self) -> None:
        """
        Close the store after flushing remaining buffer.

        After closing, the store will reject new operations.

        Raises:
            ModelOnexError: If final flush fails.
        """
        try:
            await self.flush()
        finally:
            self._ready = False

    async def clear(self) -> None:
        """
        Remove all diffs from the store.

        Clears the buffer and removes the storage file if it exists.
        Useful for testing and cleanup.

        Raises:
            ModelOnexError: If file deletion fails.
        """
        self._buffer.clear()

        if self.file_path.exists():
            try:
                self.file_path.unlink()
            except OSError as e:
                raise ModelOnexError(
                    message=f"Failed to delete storage file: {e}",
                    error_code=EnumCoreErrorCode.FILE_OPERATION_ERROR,
                    context={"path": str(self.file_path)},
                ) from e

    async def get_all(self) -> list[ModelContractDiff]:
        """
        Get all diffs in the store.

        Returns:
            List of all stored diffs, ordered by computed_at descending.
        """
        # Combine file and buffer
        all_diffs = await self._load_all()

        # Deduplicate (buffer takes precedence)
        seen_ids: set[UUID] = set()
        unique_diffs: list[ModelContractDiff] = []

        # Buffer first (more recent)
        for diff in self._buffer:
            if diff.diff_id not in seen_ids:
                seen_ids.add(diff.diff_id)
                unique_diffs.append(diff)

        # Then file
        for diff in all_diffs:
            if diff.diff_id not in seen_ids:
                seen_ids.add(diff.diff_id)
                unique_diffs.append(diff)

        # Sort by computed_at descending
        unique_diffs.sort(key=lambda d: d.computed_at, reverse=True)
        return unique_diffs

    # =========================================================================
    # Internal Methods
    # =========================================================================

    async def _load_all(self) -> list[ModelContractDiff]:
        """
        Load all diffs from the storage file.

        Returns:
            List of diffs from file. Empty list if file doesn't exist.

        Raises:
            ModelOnexError: If file reading or parsing fails.
        """
        if not self.file_path.exists():
            return []

        diffs: list[ModelContractDiff] = []

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        diff = ModelContractDiff.model_validate(data)
                        diffs.append(diff)
                    except (json.JSONDecodeError, ValueError):
                        # fallback-ok: skip malformed lines and continue reading
                        # In production, this might emit a warning event
                        continue

        except OSError as e:
            raise ModelOnexError(
                message=f"Failed to read diffs from file: {e}",
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                context={"path": str(self.file_path)},
            ) from e

        return diffs

    async def _exists_in_file(self, diff_id: UUID) -> bool:
        """
        Check if a diff with the given ID exists in the file.

        Args:
            diff_id: The UUID to check.

        Returns:
            True if found in file, False otherwise.
        """
        if not self.file_path.exists():
            return False

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        if data.get("diff_id") == str(diff_id):
                            return True
                    except json.JSONDecodeError:
                        continue

        except OSError:
            return False

        return False

    async def _rewrite_without(self, diff_id: UUID) -> None:
        """
        Rewrite the storage file excluding a specific diff.

        Args:
            diff_id: The UUID to exclude from the rewritten file.

        Raises:
            ModelOnexError: If file operations fail.
        """
        if not self.file_path.exists():
            return

        # Load all diffs except the one to remove
        all_diffs = await self._load_all()
        remaining_diffs = [d for d in all_diffs if d.diff_id != diff_id]

        try:
            # Rewrite file
            with self.file_path.open("w", encoding="utf-8") as f:
                for diff in remaining_diffs:
                    json_line = self._serialize_diff(diff)
                    f.write(json_line + "\n")

        except OSError as e:
            raise ModelOnexError(
                message=f"Failed to rewrite storage file: {e}",
                error_code=EnumCoreErrorCode.FILE_WRITE_ERROR,
                context={"path": str(self.file_path), "excluded_id": str(diff_id)},
            ) from e

    def _serialize_diff(self, diff: ModelContractDiff) -> str:
        """
        Serialize a diff to a JSON string.

        Excludes computed fields (has_changes, total_changes, change_summary)
        to allow proper deserialization with extra="forbid" model config.

        Args:
            diff: The diff to serialize.

        Returns:
            JSON string representation.

        Raises:
            ModelOnexError: If serialization fails.
        """
        try:
            # mode="json" ensures UUIDs, datetimes, and enums are serialized correctly
            # Exclude computed fields that would fail validation on reload
            # (ModelContractDiff has extra="forbid" and these are @computed_field)
            diff_dict = diff.model_dump(
                mode="json",
                exclude={"has_changes", "total_changes", "change_summary"},
            )
            return json.dumps(diff_dict, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise ModelOnexError(
                message=f"Failed to serialize diff: {e}",
                error_code=EnumCoreErrorCode.CONVERSION_ERROR,
                context={"diff_id": str(diff.diff_id)},
            ) from e


# Verify protocol compliance at module load time
_store_check: ProtocolDiffStore = ServiceDiffFileStore(base_path=Path("/tmp"))

__all__ = ["ServiceDiffFileStore"]
