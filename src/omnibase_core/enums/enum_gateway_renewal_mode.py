# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""How an ``onex`` client keeps working across gateway attach-token expiry.

Client-side mirror of ``omnibase_infra``'s ``EnumGatewayRenewalMode``
(``node_gateway_attach_effect`` contract 0.3.0, OMN-15952) -- string-identical
by construction, because the value arrives over the wire and is compared as a
string. Mirrored rather than imported: ``omnibase_core`` sits *below*
``omnibase_infra`` in the layering (compat -> core -> spi -> infra), so an
import edge in that direction is not available. The mirror is the same
precedent ``onex-api`` follows for the same model family.

One member, and the single member is the whole point of naming it on the wire
rather than assuming it:

  ``RE_ATTACH`` -- a session's ``expires_at`` is stamped once, at attach, from
  ``min(token exp, max_session_ttl_seconds)``, and nothing moves it. A
  heartbeat proves liveness and non-revocation; it does not buy time. A client
  that wants to keep working past ``expires_at`` performs a fresh
  ``client_credentials`` grant and then a fresh attach, minting a NEW
  ``session_id``.

There is deliberately no in-place-renewal member. On the node it is refused
(extending a live ceiling on the strength of a heartbeat would let a
credential Keycloak has stopped authorizing hold a session open one heartbeat
at a time); here, a client that believed in-place renewal existed would
heartbeat straight into its own expiry.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["EnumGatewayRenewalMode"]


class EnumGatewayRenewalMode(str, Enum):
    """Renewal mechanism the gateway declares to its clients."""

    RE_ATTACH = "RE_ATTACH"
