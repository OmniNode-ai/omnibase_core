"""Services module - ONEX protocol service implementations.

This module contains service implementations for ONEX protocols.

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
Always import directly from the specific service module:

    from omnibase_core.services.service_validation_suite import ServiceValidationSuite
    from omnibase_core.services.service_compute_cache import ServiceComputeCache
    from omnibase_core.services.service_handler_registry import ServiceHandlerRegistry
    from omnibase_core.services.service_parallel_executor import ServiceParallelExecutor
    from omnibase_core.services.service_timing import ServiceTiming

INCORRECT USAGE (WILL FAIL):
----------------------------
Do NOT attempt to import services from the package level:

    # This will raise ImportError - services are not exported!
    from omnibase_core.services import ServiceValidationSuite  # WRONG!

    # This will also fail
    from omnibase_core.services import *  # WRONG!

For protocol-based dependency injection, use the container:

    service = container.get_service("ProtocolValidationSuite")

See Also:
    - docs/architecture/CONTAINER_TYPES.md for DI patterns
    - OMN-1071 for the rationale behind this naming/import policy
"""

# No imports at module level to avoid circular import issues.
# Import directly from the specific service module as documented above.

__all__: list[str] = []
