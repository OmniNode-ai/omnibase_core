# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Registry services for ONEX.

This package provides in-memory thread-safe registries for ONEX metadata:
- RegistryCapability: Registry for capability metadata
- RegistryProvider: Registry for provider descriptors

================================================================================
IMPORT POLICY: NO PACKAGE-LEVEL EXPORTS (OMN-1071)
================================================================================

Registry services follow the same import policy as other services in omnibase_core.
Import directly from the specific module:

    from omnibase_core.services.registry.registry_capability import RegistryCapability
    from omnibase_core.services.registry.registry_provider import RegistryProvider

See Also:
    - omnibase_core.services.__init__ for full import policy documentation
    - OMN-1156 for registry implementation details
"""

__all__: list[str] = []
