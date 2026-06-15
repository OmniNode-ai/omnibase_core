# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact store (OMN-13093, minimal slice).

Provides :class:`ArtifactStore`, the durable-capture blob store consumed by
the skill-output suppression slice (OMN-13089) and extended in place by the
parent durable-capture plan's Phase 1.
"""

from __future__ import annotations

from omnibase_core.artifacts.artifact_store import (
    ARTIFACT_STORE_ROOT_ENV,
    WRITER_VERSION,
    ArtifactStore,
)

__all__ = [
    "ARTIFACT_STORE_ROOT_ENV",
    "WRITER_VERSION",
    "ArtifactStore",
]
