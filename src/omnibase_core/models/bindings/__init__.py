# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Binding models for ONEX capability resolution.

Models for recording the results of capability resolution,
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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.bindings.model_binding import ModelBinding
    from omnibase_core.models.bindings.model_resolution_result import (
        ModelResolutionResult,
    )

__all__ = [
    "ModelBinding",
    "ModelResolutionResult",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelBinding": ("omnibase_core.models.bindings.model_binding", "ModelBinding"),
    "ModelResolutionResult": (
        "omnibase_core.models.bindings.model_resolution_result",
        "ModelResolutionResult",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
