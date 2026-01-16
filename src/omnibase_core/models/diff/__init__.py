"""Diff storage models.

This module provides Pydantic models for diff storage operations including
query filters and storage configuration.

Key Model Components:
    ModelDiffQuery:
        Query filters for diff retrieval including contract names, time range,
        change types, and pagination.

    ModelDiffStorageConfiguration:
        Configuration for diff storage backends including backend type selection,
        retention policies, and connection parameters.

Example:
    >>> from omnibase_core.models.diff import (
    ...     ModelDiffQuery,
    ...     ModelDiffStorageConfiguration,
    ... )
    >>> from datetime import datetime, UTC, timedelta
    >>>
    >>> # Create a query for recent diffs with changes
    >>> query = ModelDiffQuery(
    ...     has_changes=True,
    ...     computed_after=datetime.now(UTC) - timedelta(days=7),
    ...     limit=50,
    ... )
    >>>
    >>> # Create storage configuration
    >>> config = ModelDiffStorageConfiguration(
    ...     retention_days=30,
    ...     max_diffs=10000,
    ... )

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_diff_store.ProtocolDiffStore`:
      Protocol using these models
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory storage implementation

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
from omnibase_core.models.diff.model_diff_storage_configuration import (
    ModelDiffStorageConfiguration,
)

__all__ = [
    "ModelDiffQuery",
    "ModelDiffStorageConfiguration",
]
