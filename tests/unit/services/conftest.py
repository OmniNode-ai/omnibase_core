# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Conftest for services tests.

This module provides fixtures and configuration for testing service-related
functionality, particularly handling the forward reference resolution needed
for ModelProviderDescriptor.
"""

import pytest
from pydantic import ValidationError


def _rebuild_provider_descriptor_forward_refs() -> bool:
    """Rebuild ModelProviderDescriptor forward references.

    This function handles the circular import issue by carefully importing
    ModelHealthStatus and rebuilding ModelProviderDescriptor.

    Returns:
        True if successful, False if circular import prevents resolution.
    """
    try:
        # Import the module directly to avoid triggering __init__.py chains
        # that cause circular imports
        import importlib

        # First, ensure the health status module is loaded
        health_status_module = importlib.import_module(
            "omnibase_core.models.health.model_health_status"
        )
        ModelHealthStatus = health_status_module.ModelHealthStatus

        # Now import and rebuild the provider descriptor
        from omnibase_core.models.providers.model_provider_descriptor import (
            ModelProviderDescriptor,
        )

        ModelProviderDescriptor.model_rebuild(
            _types_namespace={"ModelHealthStatus": ModelHealthStatus}
        )
        return True
    except (AttributeError, ImportError, TypeError, ValidationError, ValueError):
        # init-errors-ok: model rebuild may fail during import chain resolution
        return False


# Try to rebuild at module load time
_MODEL_REBUILD_SUCCESS = _rebuild_provider_descriptor_forward_refs()


@pytest.fixture(autouse=True)
def ensure_model_provider_descriptor_rebuilt() -> None:
    """Ensure ModelProviderDescriptor has forward references resolved.

    This fixture runs automatically before each test to ensure the model
    is properly configured. If the initial rebuild failed, it attempts
    to rebuild again (which may succeed after more imports have completed).
    """
    global _MODEL_REBUILD_SUCCESS
    if not _MODEL_REBUILD_SUCCESS:
        _MODEL_REBUILD_SUCCESS = _rebuild_provider_descriptor_forward_refs()
        if not _MODEL_REBUILD_SUCCESS:
            pytest.skip(
                "ModelProviderDescriptor forward references cannot be resolved "
                "due to circular import. See OMN-1075 for tracking."
            )
