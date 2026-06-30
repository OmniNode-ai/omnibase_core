# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Artifact redaction states (OMN-13152).

The closed set of redaction states recorded on an artifact's metadata sidecar.
``SECRET_DETECTED`` is terminal for the raw bytes: the store refuses to persist
raw content once a secret is detected.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumArtifactRedactionState"]


class EnumArtifactRedactionState(StrEnum):
    """Redaction state of a stored artifact's bytes."""

    RAW = "raw"
    """Unmodified original bytes (no redaction applied)."""

    REDACTED = "redacted"
    """A redaction transform has been applied; the stored bytes are sanitized."""

    RESTRICTED = "restricted"
    """Bytes are intact but read access is gated behind authorization."""

    SECRET_DETECTED = "secret_detected"  # pragma: allowlist secret
    """A secret was detected; raw bytes were refused and never persisted."""
