"""Diff storage service module.

This module provides services for storing and querying contract diffs.
The diff storage infrastructure enables persistence and retrieval of
contract diff results for auditing and analysis.

================================================================================
IMPORT POLICY: NO PACKAGE-LEVEL EXPORTS (OMN-1071)
================================================================================

Services are intentionally NOT exported at the package level. This is a deliberate
design decision to prevent circular import issues that arise from the complex
dependency graph between services, protocols, and models in the ONEX framework.

WHY THIS POLICY EXISTS:
-----------------------
1. Services depend on protocols, models, and other services
2. Package-level imports execute at module load time
3. This creates circular dependencies when services reference each other
4. Explicit module-level imports break these cycles by deferring resolution

CORRECT USAGE:
--------------
Always import directly from the specific module:

    from omnibase_core.services.diff.service_diff_in_memory_store import ServiceDiffInMemoryStore
    from omnibase_core.protocols.storage.protocol_diff_store import ProtocolDiffStore
    from omnibase_core.models.diff.model_diff_query import ModelDiffQuery
    from omnibase_core.models.diff.model_diff_storage_configuration import (
        ModelDiffStorageConfiguration,
    )

INCORRECT USAGE (WILL FAIL):
----------------------------
Do NOT attempt to import from the package level:

    # This will raise ImportError - not exported!
    from omnibase_core.services.diff import ServiceDiffInMemoryStore  # WRONG!

For protocol-based dependency injection, use the container:

    service = container.get_service("ProtocolDiffStore")

See Also:
    - docs/architecture/CONTAINER_TYPES.md for DI patterns
    - OMN-1071 for the rationale behind this naming/import policy

.. versionadded:: 0.6.0
    Added as part of Diff Storage Infrastructure (OMN-1149)
"""

# No imports at module level to avoid circular import issues.
# Import directly from the specific module as documented above.

__all__: list[str] = []
