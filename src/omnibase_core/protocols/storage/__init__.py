"""Storage protocol definitions.

This module provides protocols for pluggable storage backends.
Currently supports:

- ProtocolDiffStore: Interface for contract diff storage backends

Example:
    >>> from omnibase_core.protocols.storage import ProtocolDiffStore
    >>> from omnibase_core.services.diff.service_diff_in_memory_store import ServiceDiffInMemoryStore
    >>>
    >>> # ServiceDiffInMemoryStore implements ProtocolDiffStore
    >>> store: ProtocolDiffStore = ServiceDiffInMemoryStore()

See Also:
    - :class:`~omnibase_core.services.diff.service_diff_in_memory_store.ServiceDiffInMemoryStore`:
      In-memory implementation
    - :class:`~omnibase_core.models.contracts.diff.ModelContractDiff`:
      The diff model being stored

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore

__all__ = ["ProtocolDiffStore", "ProtocolTraceStore"]
