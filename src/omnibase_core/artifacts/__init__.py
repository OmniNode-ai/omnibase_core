# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact store (OMN-13093 slice; OMN-13152 Phase 1).

Provides :class:`ArtifactStore`, the durable-capture blob store consumed by
the skill-output suppression slice (OMN-13089) and hardened in place by the
durable-capture plan's Phase 1 (retention, quota, redaction, restricted-tier
read authorization).
"""

from __future__ import annotations

from omnibase_core.artifacts.artifact_store import (
    ARTIFACT_STORE_ROOT_ENV,
    DEFAULT_READ_CHUNK_BYTES,
    RESTRICTED_ARTIFACT_KINDS,
    WRITER_VERSION,
    ArtifactQuotaExceededError,
    ArtifactSecretDetectedError,
    ArtifactStore,
    ArtifactUnauthorizedError,
    SecretDetector,
)

__all__ = [
    "ARTIFACT_STORE_ROOT_ENV",
    "DEFAULT_READ_CHUNK_BYTES",
    "RESTRICTED_ARTIFACT_KINDS",
    "WRITER_VERSION",
    "ArtifactQuotaExceededError",
    "ArtifactSecretDetectedError",
    "ArtifactStore",
    "ArtifactUnauthorizedError",
    "SecretDetector",
]
