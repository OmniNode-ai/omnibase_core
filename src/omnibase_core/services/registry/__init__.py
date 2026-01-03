# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
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

Deprecated Aliases (OMN-1222)
=============================
This module provides deprecated aliases for classes renamed in PR #319.
The following aliases will be removed in v0.5.0:

- ``RegistryCapability`` -> use ``ServiceRegistryCapability``
- ``RegistryProvider`` -> use ``ServiceRegistryProvider``

The ``__getattr__`` function provides lazy loading with deprecation warnings
to help users migrate to the new names.
"""

from typing import Any

__all__: list[str] = [
    # DEPRECATED: Use ServiceRegistryCapability from service_registry_capability instead
    "RegistryCapability",
    # DEPRECATED: Use ServiceRegistryProvider from service_registry_provider instead
    "RegistryProvider",
]


# =============================================================================
# Deprecated aliases: Lazy-load with warnings per OMN-1222 renaming.
# TODO: Remove in v0.5.0
# =============================================================================
def __getattr__(name: str) -> Any:
    """
    Lazy loading for deprecated aliases per OMN-1222 renaming.

    Deprecated Aliases:
    -------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - RegistryCapability -> ServiceRegistryCapability
    - RegistryProvider -> ServiceRegistryProvider
    """
    import warnings

    if name == "RegistryCapability":
        warnings.warn(
            "'RegistryCapability' is deprecated, use 'ServiceRegistryCapability' "
            "from 'omnibase_core.services.registry.service_registry_capability' instead. "
            "This alias will be removed in v0.5.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        from omnibase_core.services.registry.service_registry_capability import (
            ServiceRegistryCapability,
        )

        return ServiceRegistryCapability

    if name == "RegistryProvider":
        warnings.warn(
            "'RegistryProvider' is deprecated, use 'ServiceRegistryProvider' "
            "from 'omnibase_core.services.registry.service_registry_provider' instead. "
            "This alias will be removed in v0.5.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        from omnibase_core.services.registry.service_registry_provider import (
            ServiceRegistryProvider,
        )

        return ServiceRegistryProvider

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )
