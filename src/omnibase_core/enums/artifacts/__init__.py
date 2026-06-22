# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Artifact-store-scoped enums (OMN-13152).

Retention classes and redaction states for the durable-capture
:class:`~omnibase_core.artifacts.artifact_store.ArtifactStore` Phase 1
hardening. These are distinct from the compliance-lifecycle
``EnumRetentionPolicy`` and the delegation-envelope ``EnumRedactionPolicy``:
they are the closed value sets the artifact-store write/read path enforces.
"""

from __future__ import annotations

from omnibase_core.enums.artifacts.enum_artifact_redaction_state import (
    EnumArtifactRedactionState,
)
from omnibase_core.enums.artifacts.enum_artifact_retention_class import (
    EnumArtifactRetentionClass,
)

__all__ = [
    "EnumArtifactRedactionState",
    "EnumArtifactRetentionClass",
]
