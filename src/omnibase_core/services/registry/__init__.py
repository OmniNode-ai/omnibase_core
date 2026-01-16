"""
Registry services for ONEX.

This package provides in-memory thread-safe registries for ONEX metadata:
- ServiceRegistryCapability: Registry for capability metadata
- ServiceRegistryProvider: Registry for provider descriptors

================================================================================
IMPORT POLICY: NO PACKAGE-LEVEL EXPORTS (OMN-1071)
================================================================================

Registry services follow the same import policy as other services in omnibase_core.
Import directly from the specific module:

    from omnibase_core.services.registry.service_registry_capability import ServiceRegistryCapability
    from omnibase_core.services.registry.service_registry_provider import ServiceRegistryProvider

See Also:
    - omnibase_core.services.__init__ for full import policy documentation
    - OMN-1156 for registry implementation details
"""
