# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact models.

Provides ``ModelArtifactRef``, the canonical ``sha256:<hex>`` reference type
for the durable-capture artifact store (OMN-13091).
"""

from __future__ import annotations

from omnibase_core.models.artifacts.model_artifact_ref import ModelArtifactRef

__all__ = [
    "ModelArtifactRef",
]
