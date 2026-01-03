# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Conftest for services tests.

This module handles forward reference resolution for Pydantic models used in
services tests. The ModelProviderDescriptor model has a forward reference to
ModelHealthStatus that must be resolved before instances can be created.

The approach uses a session-scoped autouse fixture that:
1. Imports ServiceRegistryProvider first (triggers the normal import chain)
2. Gets ModelHealthStatus from sys.modules
3. Calls model_rebuild() with the proper namespace

This works because pytest fixtures run after all module-level code has executed,
so the health module's ModelHealthStatus class is available in sys.modules.
"""

import sys

import pytest

from omnibase_core.models.providers import ModelProviderDescriptor


@pytest.fixture(scope="session", autouse=True)
def _rebuild_model_provider_descriptor() -> None:
    """Rebuild ModelProviderDescriptor to resolve forward reference to ModelHealthStatus.

    This fixture is session-scoped and autouse=True, meaning it runs once before
    any tests in this directory execute. It ensures that the forward reference
    to ModelHealthStatus is properly resolved.
    """
    # The health module should be loaded through normal import chains
    # (e.g., through mixins, services, etc.)
    health_module_name = "omnibase_core.models.health.model_health_status"

    if health_module_name not in sys.modules:
        # Force load the health module by importing through mixins
        # This triggers the import chain that loads model_health_status
        try:
            from omnibase_core.mixins.mixin_health_check import (  # noqa: F401
                MixinHealthCheck,
            )
        except ImportError:
            pass

    if health_module_name in sys.modules:
        health_module = sys.modules[health_module_name]
        ModelHealthStatus = getattr(health_module, "ModelHealthStatus", None)

        if ModelHealthStatus is not None:
            # Rebuild with the ModelHealthStatus class in the namespace
            ModelProviderDescriptor.model_rebuild(
                _types_namespace={"ModelHealthStatus": ModelHealthStatus}
            )
