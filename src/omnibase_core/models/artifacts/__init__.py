# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact models.

Provides ``ModelArtifactRef`` (the canonical ``sha256:<hex>`` reference type,
OMN-13091), the typed metadata sidecar ``ModelArtifactMetadata``, and the
read-time authorization context ``ModelArtifactAuthContext`` (OMN-13152).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.artifacts.model_artifact_auth_context import (
        ModelArtifactAuthContext,
    )
    from omnibase_core.models.artifacts.model_artifact_metadata import (
        ModelArtifactMetadata,
    )
    from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef

__all__ = [
    "ModelArtifactAuthContext",
    "ModelArtifactMetadata",
    "ModelArtifactRef",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelArtifactAuthContext": (
        "omnibase_core.models.artifacts.model_artifact_auth_context",
        "ModelArtifactAuthContext",
    ),
    "ModelArtifactMetadata": (
        "omnibase_core.models.artifacts.model_artifact_metadata",
        "ModelArtifactMetadata",
    ),
    "ModelArtifactRef": (
        "omnibase_core.models.artifacts.model_artifact_ref",
        "ModelArtifactRef",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
