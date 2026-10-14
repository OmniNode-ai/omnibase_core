# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The error a sprint roll raises when Linear does not hold what it wrote (OMN-21085)."""

from __future__ import annotations

from omnibase_core.nodes.node_sprint_roll_apply_effect.node_linear_transport_error import (
    NodeLinearTransportError,
)

__all__ = ["NodeSprintRollReadbackError"]


class NodeSprintRollReadbackError(NodeLinearTransportError):
    """An issue read back after its update differs from what the update sent.

    A subclass of the transport error so a caller that already stops on a failed Linear
    call stops on this too: an `issueUpdate` that answers `success` and leaves the
    milestone blank is the failure the 2026-10-12 roll would have shipped, and reporting
    it as a write would hide it. The journal line is already on disk, so the undo still
    covers the ticket.
    """
