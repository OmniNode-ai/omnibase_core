# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelGatewaySession — the attach session record, as read by an ``onex`` client.

Client-side mirror of ``omnibase_infra``'s ``ModelGatewaySession``
(``node_gateway_attach_effect``, OMN-15750) and of the ``onex-api`` edge's
``ModelGatewaySessionWire``, field-for-field. Mirrored rather than imported
because ``omnibase_core`` sits below ``omnibase_infra`` in the layering.

``extra="forbid"`` is load-bearing on a mirror: it turns a producer that grows
a field into a loud parse failure on the next release rather than a client
that silently ignores whatever it was told. ``expires_at`` in particular is
stamped once at attach and moved by nothing -- the client reads it as the hard
ceiling its renewal cycle races, so a silently-dropped or misread value would
show up as a session that dies mid-flight.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_gateway_session_status import EnumGatewaySessionStatus

__all__ = ["ModelGatewaySession"]


class ModelGatewaySession(BaseModel):
    """One tenant edge's attach session, as returned by the gateway."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    session_id: UUID
    tenant_id: UUID
    tenant_slug: str
    principal_id: str
    keycloak_client_id: str
    edge_instance_id: str
    status: EnumGatewaySessionStatus
    attached_at: datetime
    last_heartbeat_at: datetime
    # Never later than the access token's own exp, clamped by the node's
    # max_session_ttl_seconds. Immutable for the life of this session_id.
    expires_at: datetime
