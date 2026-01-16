"""
Binding models for ONEX capability resolution.

This module provides models for recording the results of capability resolution,
where capability dependencies are matched to concrete providers.

Core Principle:
    "Bindings are the output of resolution - they record which provider
    was selected to satisfy a capability dependency."

Key Models
----------
ModelBinding
    Records the resolution of a capability dependency to a provider.
    Captures what was requested, what was selected, and resolution metadata.

ModelResolutionResult
    Complete resolution result with bindings and audit information.
    Captures the outcome of resolving all capability dependencies for a
    handler contract.

Resolution Flow
---------------
The capability resolution system uses these model types:

1. **ModelCapabilityDependency** (input):
   Declares what capability is needed, with requirements.

2. **ModelProviderDescriptor** (registry):
   Describes available providers with their capabilities.

3. **ModelBinding** (output):
   Records which provider was selected for each dependency.

4. **ModelResolutionResult** (aggregate output):
   Collects all bindings with audit information about the resolution process.

Example Usage
-------------
Creating a binding after resolution:

    >>> from datetime import datetime, timezone
    >>> from omnibase_core.models.bindings import ModelBinding
    >>>
    >>> binding = ModelBinding(
    ...     dependency_alias="db",
    ...     capability="database.relational",
    ...     resolved_provider="550e8400-e29b-41d4-a716-446655440000",
    ...     adapter="omnibase_infra.adapters.PostgresAdapter",
    ...     connection_ref="secrets://postgres/primary",
    ...     requirements_hash="sha256:abc123",
    ...     resolution_profile="production",
    ...     resolved_at=datetime.now(timezone.utc),
    ...     resolution_notes=["Selected based on transaction support"],
    ...     candidates_considered=3,
    ... )

Creating a resolution result:

    >>> from omnibase_core.models.bindings import ModelResolutionResult
    >>>
    >>> result = ModelResolutionResult(
    ...     bindings={"db": binding},
    ...     success=True,
    ...     candidates_by_alias={"db": ["provider-1", "provider-2"]},
    ...     scores_by_alias={"db": {"provider-1": 0.95, "provider-2": 0.7}},
    ... )
    >>>
    >>> result.is_successful
    True
    >>> result.binding_count
    1

Thread Safety
-------------
All models in this module are immutable (frozen=True) after creation,
making them thread-safe for concurrent read access.

See Also
--------
omnibase_core.models.capabilities : Capability dependency models
omnibase_core.models.providers : Provider descriptor models

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1155 capability resolution models.
"""

from omnibase_core.models.bindings.model_binding import ModelBinding
from omnibase_core.models.bindings.model_resolution_result import ModelResolutionResult

__all__ = [
    "ModelBinding",
    "ModelResolutionResult",
]
