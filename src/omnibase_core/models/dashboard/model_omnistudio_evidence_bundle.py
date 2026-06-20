# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelOmniStudioEvidenceBundle — a tamper-evident bundle of review packets.

OMN-13387 (epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md). An
OmniStudio session produces one or more :class:`ModelReviewPacket` instances;
this bundle aggregates them under a stable session identifier and exposes a
deterministic ``compute_bundle_fingerprint`` that is order-independent — the
fingerprint is computed over the *sorted* set of per-packet hashes, so the same
packets in any order yield the same fingerprint. The bundle is frozen and
``extra="forbid"``.
"""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_review_packet import ModelReviewPacket

__all__ = ["ModelOmniStudioEvidenceBundle"]


class ModelOmniStudioEvidenceBundle(BaseModel):
    """A deterministic, order-independent bundle of review packets.

    ``session_id`` is the stable semantic identifier for the OmniStudio session
    that produced the bundle. ``packets`` is the immutable tuple of review
    packets gathered during the session. ``compute_bundle_fingerprint`` hashes
    the sorted per-packet hashes so bundle equality does not depend on packet
    ordering.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    session_id: str = Field(  # string-id-ok: semantic session label, not a UUID
        ...,
        description="Stable semantic identifier for the OmniStudio review session",
        min_length=1,
    )
    packets: tuple[ModelReviewPacket, ...] = Field(
        default=(),
        description="Immutable tuple of review packets gathered in this session",
    )

    def compute_bundle_fingerprint(self) -> str:
        """Return a deterministic, order-independent ``sha256:<hex>`` fingerprint.

        Each packet contributes its :meth:`ModelReviewPacket.compute_packet_hash`;
        the per-packet hashes are sorted before being joined and hashed so the
        fingerprint is invariant under packet reordering.
        """
        packet_hashes = sorted(packet.compute_packet_hash() for packet in self.packets)
        joined = "\n".join([self.session_id, *packet_hashes])
        digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"
