"""Trace recording service module.

This module provides services for recording and querying execution traces.
The trace recording infrastructure enables observability and replay capabilities.

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

    from omnibase_core.services.trace.service_trace_recording import ServiceTraceRecording
    from omnibase_core.services.trace.service_trace_in_memory_store import ServiceTraceInMemoryStore
    from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore
    from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
    from omnibase_core.models.trace_query.model_trace_summary import ModelTraceSummary

INCORRECT USAGE (WILL FAIL):
----------------------------
Do NOT attempt to import from the package level:

    # This will raise ImportError - not exported!
    from omnibase_core.services.trace import ServiceTraceRecording  # WRONG!

For protocol-based dependency injection, use the container:

    service = container.get_service("ProtocolTraceStore")

See Also:
    - docs/architecture/CONTAINER_TYPES.md for DI patterns
    - OMN-1071 for the rationale behind this naming/import policy

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

# No imports at module level to avoid circular import issues.
# Import directly from the specific module as documented above.

__all__: list[str] = []
