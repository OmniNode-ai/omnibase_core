# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact models.

Provides ``ModelArtifactRef`` (the canonical ``sha256:<hex>`` reference type,
OMN-13091), the typed metadata sidecar ``ModelArtifactMetadata``, and the
read-time authorization context ``ModelArtifactAuthContext`` (OMN-13152).
"""

from __future__ import annotations

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
