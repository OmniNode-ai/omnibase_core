# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ServiceGatewaySessionClient — Bearer on every gateway call (OMN-15922).

The one place a gateway request is constructed, so that a token is never
hand-passed and no code path can produce an anonymous call. Every request here
goes through ``_post``, which takes the Authorization header from the minter
rather than from an argument -- an anonymous call is not something a caller can
express, which is a stronger property than every caller remembering to pass one.

THE RENEWAL CYCLE THIS IMPLEMENTS (OMN-15952, contract 0.3.0)
    ``expires_at`` is stamped once at attach, from
    ``min(token exp, max_session_ttl_seconds)``, and nothing moves it. A
    heartbeat proves liveness and non-revocation; it buys no time. So
    ``ensure_attached`` does not "renew" -- inside the jitter window it performs
    a fresh ``client_credentials`` grant and a fresh attach, minting a NEW
    ``session_id``. Continuity across the boundary is this object's property,
    never the session record's.

FAIL-CLOSED
    An expired session is refused locally, before a request is sent: the client
    already holds ``expires_at``, so spending a round trip to be told what it
    knows is both slower and, if the gateway is unreachable, indistinguishable
    from an outage. A rejected call raises. There is no branch on which a dead
    session is used and no branch on which failure degrades to a local path --
    a locally-successful delegation while the operator believes it ran in cloud
    is the exact failure this refusal exists to prevent.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gateway.model_gateway_attachment import ModelGatewayAttachment
from omnibase_core.models.gateway.model_gateway_credential import ModelGatewayCredential
from omnibase_core.models.gateway.model_gateway_renewal_directive import (
    ModelGatewayRenewalDirective,
)
from omnibase_core.models.gateway.model_gateway_session import ModelGatewaySession
from omnibase_core.protocols.http.protocol_gateway_transport import (
    ProtocolGatewayTransport,
)
from omnibase_core.protocols.http.protocol_http_client import ProtocolHttpResponse
from omnibase_core.services.gateway.service_gateway_renewal_planner import (
    ServiceGatewayRenewalPlanner,
)
from omnibase_core.services.gateway.service_gateway_token_minter import (
    ServiceGatewayTokenMinter,
)

__all__ = ["ServiceGatewaySessionClient"]

_ATTACH_PATH: Final[str] = "/v1/gateway/attach"
_HEARTBEAT_PATH: Final[str] = "/v1/gateway/heartbeat"

# Seconds this client needs for a grant plus an attach plus one backoff-retry.
# Checked against the directive's remaining lead before a renewal is attempted.
_RENEWAL_LEAD_SECONDS: Final[int] = 30


class ServiceGatewaySessionClient:
    """Attaches to the gateway and keeps the session alive by re-attaching."""

    def __init__(
        self,
        *,
        transport: ProtocolGatewayTransport,
        credential: ModelGatewayCredential,
        minter: ServiceGatewayTokenMinter,
        rng: random.Random,
        planner: ServiceGatewayRenewalPlanner | None = None,
    ) -> None:
        self._transport = transport
        self._credential = credential
        self._minter = minter
        self._rng = rng
        self._planner = (
            planner if planner is not None else ServiceGatewayRenewalPlanner()
        )
        self._attachment: ModelGatewayAttachment | None = None
        self._renew_at: datetime | None = None

    @property
    def attachment(self) -> ModelGatewayAttachment | None:
        """The session currently held, or None before the first attach."""
        return self._attachment

    async def attach(self, *, now: datetime) -> ModelGatewayAttachment:
        """Open a new session, replacing any this client already held.

        Raises:
            ModelOnexError: If the grant fails, the gateway rejects the token,
                or the response omits the required renewal directive.
        """
        # force_fresh_token: the session ceiling is stamped from the token's
        # own exp, so attaching with a cached token that is merely still-valid
        # buys only the token's remaining life. On the renewal path that would
        # mint a successor already inside its own renewal window.
        response = await self._post(
            _ATTACH_PATH,
            payload={"edge_instance_id": self._credential.edge_instance_id},
            now=now,
            force_fresh_token=True,
        )
        body = await self._require_ok(response, operation="attach")
        attachment = self._parse_attachment(body)

        # Draw this client's own moment inside the declared jitter window, once
        # per session -- redrawing per call would let a fleet re-synchronise on
        # whichever draw happened to fire first.
        self._attachment = attachment
        self._renew_at = self._planner.plan_instant(attachment.renewal, rng=self._rng)
        return attachment

    async def heartbeat(self, *, now: datetime) -> ModelGatewaySession:
        """Prove liveness on the held session. Never extends ``expires_at``.

        Raises:
            ModelOnexError: If no session is held, if the held session has
                passed its ceiling (refused locally -- see module docstring),
                or if the gateway rejects the call.
        """
        attachment = self._require_attachment()
        if now >= attachment.session.expires_at:
            raise ModelOnexError(
                "gateway session "
                f"{attachment.session.session_id} expired at "
                f"{attachment.session.expires_at.isoformat()}; a heartbeat "
                "cannot extend it (renewal mode is "
                f"{attachment.renewal.mode.value}). Call ensure_attached() to "
                "re-attach with a fresh grant.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        response = await self._post(
            _HEARTBEAT_PATH,
            payload={"session_id": str(attachment.session.session_id)},
            now=now,
        )
        body = await self._require_ok(response, operation="heartbeat")
        document = self._decode_object(body, source="gateway heartbeat response")
        session = ModelGatewaySession.model_validate(
            self._require_mapping(document, "session")
        )

        # The contract's central negative, checked on the receiving side: if a
        # heartbeat ever comes back with a moved ceiling, that is a server-side
        # regression, and a client that silently adopted the new value would
        # hide it.
        if session.expires_at != attachment.session.expires_at:
            raise ModelOnexError(
                "gateway heartbeat returned a session whose expires_at moved "
                f"({attachment.session.expires_at.isoformat()} -> "
                f"{session.expires_at.isoformat()}). expires_at is stamped once "
                "at attach; a heartbeat must never extend it.",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return session

    async def ensure_attached(self, *, now: datetime) -> ModelGatewayAttachment:
        """Return a session valid at ``now``, re-attaching when the cycle says to.

        Re-attaches when the jitter window has opened (or the ceiling has
        already passed). Re-attaching is a fresh grant plus a fresh attach --
        a NEW ``session_id`` -- never an extension of the incumbent.
        """
        attachment = self._attachment
        renew_at = self._renew_at
        if attachment is None or renew_at is None:
            return await self.attach(now=now)

        if now < renew_at and now < attachment.session.expires_at:
            return attachment
        return await self.attach(now=now)

    def assert_renewal_is_reachable(self, *, now: datetime) -> None:
        """Raise if the held session's renewal window is too tight to complete.

        Deliberately NOT called from ``ensure_attached``: at or past
        ``renew_at`` the honest action is to re-attach immediately, and a guard
        there would turn every on-deadline renewal into a hard error. This is a
        diagnostic for ``onex auth status`` and for a supervisor deciding
        whether a deployment's ``renewal_margin_seconds`` is survivable, which
        is a question about the configuration rather than about this call.
        """
        attachment = self._require_attachment()
        self._planner.assert_window_is_honourable(
            attachment.renewal,
            now=now,
            minimum_lead_seconds=_RENEWAL_LEAD_SECONDS,
        )

    # -- transport ---------------------------------------------------------

    async def _post(
        self,
        path: str,
        *,
        payload: dict[str, str],
        now: datetime,
        force_fresh_token: bool = False,
    ) -> ProtocolHttpResponse:
        """The single gateway request constructor. Always Bearer-authenticated.

        The token goes in the Authorization header and nowhere else -- the
        gateway's own seam table binds ``Authorization: Bearer <token>`` to the
        bus command's ``access_token`` field, so a client that also placed it
        in the body would be duplicating a credential into a payload that gets
        logged and forwarded.
        """
        token = await self._minter.token_for(now=now, force_refresh=force_fresh_token)
        return await self._transport.post_json(
            self._credential.base_url.rstrip("/") + path,
            body=json.dumps(payload),
            headers={
                "Authorization": f"Bearer {token.access_token.get_secret_value()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def _require_ok(
        self, response: ProtocolHttpResponse, *, operation: str
    ) -> str:
        if response.status != 200:
            # Status only -- the remote body is not echoed into a local error
            # (see ServiceGatewayTokenMinter._grant for the same reasoning).
            raise ModelOnexError(
                f"gateway {operation} rejected (HTTP {response.status}) for "
                f"tenant '{self._credential.tenant_slug}'. If the credential was "
                "rotated or disabled, re-run 'onex auth login'.",
                error_code=EnumCoreErrorCode.AUTHENTICATION_ERROR,
            )
        return await response.text()

    # -- parsing -----------------------------------------------------------

    def _parse_attachment(self, body: str) -> ModelGatewayAttachment:
        document = self._decode_object(body, source="gateway attach response")
        if "renewal" not in document or document["renewal"] is None:
            raise ModelOnexError(
                "gateway attach response carries no 'renewal' directive. It is "
                "REQUIRED on node_gateway_attach_effect (contract 0.3.0) and "
                "optional only at the onex-api edge for rollout ordering -- a "
                "client without it has no defined behaviour at session expiry. "
                "The gateway or the edge is running a pre-OMN-15952 build.",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return ModelGatewayAttachment(
            session=ModelGatewaySession.model_validate(
                self._require_mapping(document, "session")
            ),
            heartbeat_interval_seconds=self._require_int(
                document, "heartbeat_interval_seconds"
            ),
            renewal=ModelGatewayRenewalDirective.model_validate(
                self._require_mapping(document, "renewal")
            ),
        )

    def _require_attachment(self) -> ModelGatewayAttachment:
        attachment = self._attachment
        if attachment is None:
            raise ModelOnexError(
                "no gateway session is attached; call attach() or "
                "ensure_attached() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )
        return attachment

    def _decode_object(self, raw: str, *, source: str) -> dict[str, object]:
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelOnexError(
                f"{source} is not valid JSON.",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            ) from exc
        if not isinstance(document, dict):
            raise ModelOnexError(
                f"{source} is {type(document).__name__}, expected a JSON object.",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            )
        return {str(key): value for key, value in document.items()}

    def _require_mapping(self, document: dict[str, object], key: str) -> object:
        if key not in document:
            raise ModelOnexError(
                f"gateway response has no '{key}' field.",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return document[key]

    def _require_int(self, document: dict[str, object], key: str) -> int:
        value = document.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ModelOnexError(
                f"gateway response has no usable integer '{key}' field.",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        return value
