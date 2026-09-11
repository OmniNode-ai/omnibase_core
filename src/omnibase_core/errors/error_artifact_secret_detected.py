# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed secret-detection error for the content-addressed artifact store."""

from __future__ import annotations

from omnibase_core.types.type_artifact_ref import ArtifactRefProtocol


class ArtifactSecretDetectedError(Exception):
    """Raised when raw artifact bytes contain a detected secret.

    ``ref`` remains the full content-addressed payload so callers keep the
    existing typed identity rather than a flattened string. The structural
    protocol keeps this foundation-layer error independent of ``models``.
    """

    def __init__(self, ref: ArtifactRefProtocol) -> None:
        self.ref = ref
        super().__init__(
            f"secret detected in artifact {ref.ref}; raw write refused "
            "(secret_detected sidecar recorded)"
        )


__all__ = ["ArtifactSecretDetectedError"]
