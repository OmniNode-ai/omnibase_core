# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Lifecycle status of one gateway attach session, as read by an ``onex`` client.

Client-side mirror of ``omnibase_infra``'s ``EnumGatewaySessionStatus``
(``node_gateway_attach_effect``, OMN-15750) -- string-identical, mirrored
rather than imported because ``omnibase_core`` sits below ``omnibase_infra``
in the layering.

Modelled as an enum rather than a bare ``str`` so that an unrecognised status
off the wire fails validation at the boundary instead of flowing into a
comparison that quietly never matches -- the failure mode where a client
treats a ``REVOKED`` session as merely "not ACTIVE" and keeps going.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["EnumGatewaySessionStatus"]


class EnumGatewaySessionStatus(str, Enum):
    """Status values a gateway session record may carry."""

    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    DETACHED = "DETACHED"
    REVOKED = "REVOKED"
