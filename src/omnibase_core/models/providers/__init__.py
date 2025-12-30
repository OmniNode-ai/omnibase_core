# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Provider models for ONEX framework.

This module provides models for provider-related functionality including
provider descriptors and capability requirements.

Key Models
----------
ModelProviderDescriptor
    Describes a concrete provider instance registered in the registry.
    Contains capabilities, adapter path, connection reference, and health status.
    Uses ModelHealthStatus from omnibase_core.models.health for rich health tracking.

Example Usage
-------------
Creating a provider descriptor:

    >>> from uuid import uuid4
    >>> from omnibase_core.models.providers import ModelProviderDescriptor
    >>>
    >>> descriptor = ModelProviderDescriptor(
    ...     provider_id=uuid4(),
    ...     capabilities=["database.relational", "database.postgresql"],
    ...     adapter="omnibase_infra.adapters.PostgresAdapter",
    ...     connection_ref="secrets://postgres/primary",
    ...     tags=["production", "primary"],
    ... )

Checking provider health:

    >>> from omnibase_core.models.health import ModelHealthStatus
    >>> health = ModelHealthStatus.create_healthy(score=1.0)
    >>> health.status
    'healthy'

Thread Safety
-------------
All models in this module are immutable (frozen=True) after creation,
making them thread-safe for concurrent read access from multiple threads
or async tasks.

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1153 provider registry models.
"""

from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)

__all__ = [
    "ModelProviderDescriptor",
]
