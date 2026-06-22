# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Artifact retention classes (OMN-13152).

The closed set of retention classes the durable-capture
:class:`~omnibase_core.artifacts.artifact_store.ArtifactStore` supports. Each
class maps to a configurable default TTL (seconds); ``PERMANENT`` never
expires (``None`` TTL).
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EnumArtifactRetentionClass"]

# Default TTLs in seconds per class. PERMANENT has no TTL (never expires).
_DEFAULT_TTL_SECONDS: dict[str, int | None] = {
    "ephemeral": 60 * 60,  # 1 hour
    "session": 24 * 60 * 60,  # 1 day
    "ticket": 90 * 24 * 60 * 60,  # 90 days
    "permanent": None,
}


class EnumArtifactRetentionClass(StrEnum):
    """Retention class governing how long an artifact is kept.

    The default TTL per class is a starting policy; callers may override the
    effective TTL per write. ``PERMANENT`` artifacts have no TTL and are never
    eligible for retention-driven eviction.
    """

    EPHEMERAL = "ephemeral"
    """Short-lived scratch output; default TTL 1 hour."""

    SESSION = "session"
    """Lives for the duration of a working session; default TTL 1 day."""

    TICKET = "ticket"
    """Retained for the lifetime of a ticket's work; default TTL 90 days."""

    PERMANENT = "permanent"
    """Never expires (no TTL)."""

    @property
    def default_ttl_seconds(self) -> int | None:
        """Default time-to-live in seconds, or ``None`` for ``PERMANENT``."""
        return _DEFAULT_TTL_SECONDS[self.value]
