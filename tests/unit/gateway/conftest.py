# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fakes for the ``onex auth`` gateway client tests (OMN-15922).

Everything here is a NEAR-side fake of a foreign HTTP boundary -- a fake
Keycloak token endpoint and a fake gateway attach ingress -- so the whole
credential -> JWT -> Bearer -> attach -> re-attach cycle runs with zero
network. The far side under test (the credential store, the minter, the
renewal planner, the session client) is the real implementation in every
test; only the socket is replaced. That is the distinction OMN-15910 draws:
a far-side mock would be one that stands in for the code whose behaviour the
test claims to prove, and there is none of that here.

The fake token endpoint mints structurally real JWTs (three base64url
segments, real claim payload, a placeholder signature) because the client's
audience check parses the payload segment. It does NOT sign them, and the
client deliberately does not verify signatures -- the gateway does that
against Keycloak's JWKS. See ``ServiceGatewayTokenMinter`` for why the
client-side check is a fail-fast, not a security control.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

import pytest


def encode_jwt(claims: Mapping[str, object]) -> str:
    """Build an unsigned but structurally valid JWT carrying ``claims``."""

    def segment(payload: Mapping[str, object]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = segment({"alg": "RS256", "typ": "JWT", "kid": "fake-kid"})
    body = segment(claims)
    return f"{header}.{body}.c2lnbmF0dXJl"


class FakeHttpResponse:
    """Minimal ``ProtocolHttpResponse`` stand-in over an in-memory body."""

    def __init__(self, status: int, body: str) -> None:
        self._status = status
        self._body = body

    @property
    def status(self) -> int:
        return self._status

    async def text(self) -> str:
        return self._body

    async def json(self) -> object:
        return json.loads(self._body)


class FakeGatewayTransport:
    """Fake token endpoint + fake gateway attach ingress on one seam.

    Records every request so tests can assert on the Bearer actually sent and
    on the secret never appearing where it must not.
    """

    def __init__(
        self,
        *,
        token_endpoint: str,
        gateway_base_url: str,
        client_id: str,
        client_secret: str,
        audiences: Sequence[str] = ("gateway-attach",),
        token_ttl_seconds: int = 900,
        session_ttl_seconds: int = 900,
        heartbeat_interval_seconds: int = 15,
        renewal_margin_seconds: int = 120,
        renewal_jitter_seconds: int = 30,
        tenant_slug: str = "acme",
    ) -> None:
        self._token_endpoint = token_endpoint
        self._gateway_base_url = gateway_base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self.audiences = list(audiences)
        self._token_ttl_seconds = token_ttl_seconds
        self._session_ttl_seconds = session_ttl_seconds
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._renewal_margin_seconds = renewal_margin_seconds
        self._renewal_jitter_seconds = renewal_jitter_seconds
        self._tenant_slug = tenant_slug
        self.now = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)
        self.form_requests: list[tuple[str, Mapping[str, str]]] = []
        self.json_requests: list[tuple[str, str, Mapping[str, str]]] = []
        self.issued_tokens: list[str] = []
        self.attach_count = 0
        self.revoked = False
        self.token_endpoint_status = 200
        self.session_serial = 0
        # The ceiling is stamped ONCE, at attach, and no later call moves it --
        # a fake that recomputed it per heartbeat would silently satisfy a
        # client that believed heartbeats extend sessions.
        self.current_session: dict[str, object] | None = None

    # -- fake Keycloak -----------------------------------------------------
    async def post_form(
        self,
        url: str,
        *,
        form: Mapping[str, str],
        headers: Mapping[str, str],
    ) -> FakeHttpResponse:
        self.form_requests.append((url, dict(form)))
        if url != self._token_endpoint:
            return FakeHttpResponse(404, '{"error":"not_found"}')
        if self.token_endpoint_status != 200:
            return FakeHttpResponse(
                self.token_endpoint_status, '{"error":"invalid_client"}'
            )
        if form.get("grant_type") != "client_credentials":
            return FakeHttpResponse(400, '{"error":"unsupported_grant_type"}')
        if (
            form.get("client_id") != self._client_id
            or form.get("client_secret") != self._client_secret
        ):
            return FakeHttpResponse(401, '{"error":"invalid_client"}')
        if self.revoked:
            return FakeHttpResponse(401, '{"error":"invalid_client"}')
        exp = self.now + timedelta(seconds=self._token_ttl_seconds)
        aud: object = (
            self.audiences[0] if len(self.audiences) == 1 else list(self.audiences)
        )
        token = encode_jwt(
            {
                "aud": aud,
                "exp": int(exp.timestamp()),
                "iat": int(self.now.timestamp()),
                "iss": "https://keycloak.invalid/realms/acme",
                "sub": self._client_id,
                "azp": self._client_id,
                "tenant_slug": self._tenant_slug,
            }
        )
        self.issued_tokens.append(token)
        body = json.dumps(
            {
                "access_token": token,
                "expires_in": self._token_ttl_seconds,
                "token_type": "Bearer",
                "not-before-policy": 0,
                "scope": "profile email",
            }
        )
        return FakeHttpResponse(200, body)

    # -- fake gateway ------------------------------------------------------
    async def post_json(
        self,
        url: str,
        *,
        body: str,
        headers: Mapping[str, str],
    ) -> FakeHttpResponse:
        self.json_requests.append((url, body, dict(headers)))
        authorization = headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return FakeHttpResponse(401, '{"detail":"missing bearer"}')
        presented = authorization.removeprefix("Bearer ")
        if self.revoked or presented not in self.issued_tokens:
            return FakeHttpResponse(401, '{"detail":"token rejected"}')
        if url == f"{self._gateway_base_url}/v1/gateway/attach":
            return self._attach()
        if url == f"{self._gateway_base_url}/v1/gateway/heartbeat":
            return self._heartbeat()
        return FakeHttpResponse(404, '{"detail":"not found"}')

    def _new_session_payload(self) -> dict[str, object]:
        attached = self.now
        expires = attached + timedelta(seconds=self._session_ttl_seconds)
        return {
            "session_id": f"11111111-1111-4111-8111-{self.session_serial:012d}",
            "tenant_id": "22222222-2222-4222-8222-222222222222",
            "tenant_slug": self._tenant_slug,
            "principal_id": self._client_id,
            "keycloak_client_id": self._client_id,
            "edge_instance_id": "test-edge",
            "status": "ACTIVE",
            "attached_at": attached.isoformat(),
            "last_heartbeat_at": attached.isoformat(),
            "expires_at": expires.isoformat(),
        }

    def _attach(self) -> FakeHttpResponse:
        self.attach_count += 1
        self.session_serial += 1
        session = self._new_session_payload()
        self.current_session = session
        expires = datetime.fromisoformat(str(session["expires_at"]))
        renew_at = expires - timedelta(seconds=self._renewal_margin_seconds)
        renew_not_before = renew_at - timedelta(seconds=self._renewal_jitter_seconds)
        payload = {
            "session": session,
            "heartbeat_interval_seconds": self._heartbeat_interval_seconds,
            "renewal": {
                "mode": "RE_ATTACH",
                "session_expires_at": expires.isoformat(),
                "renew_not_before": renew_not_before.isoformat(),
                "renew_at": renew_at.isoformat(),
                "margin_seconds": self._renewal_margin_seconds,
                "jitter_seconds": self._renewal_jitter_seconds,
            },
            "session_event": {
                "event_type": "ATTACHED",
                "session_id": session["session_id"],
                "tenant_id": session["tenant_id"],
                "tenant_slug": self._tenant_slug,
                "principal_id": self._client_id,
                "edge_instance_id": "test-edge",
                "emitted_at": self.now.isoformat(),
            },
        }
        return FakeHttpResponse(200, json.dumps(payload))

    def _heartbeat(self) -> FakeHttpResponse:
        if self.current_session is None:
            return FakeHttpResponse(404, '{"detail":"no session"}')
        session = dict(self.current_session)
        session["last_heartbeat_at"] = self.now.isoformat()
        payload = {
            "session": session,
            "revoked": False,
            "session_event": {
                "event_type": "HEARTBEAT",
                "session_id": session["session_id"],
                "tenant_id": session["tenant_id"],
                "tenant_slug": self._tenant_slug,
                "principal_id": self._client_id,
                "edge_instance_id": "test-edge",
                "emitted_at": self.now.isoformat(),
            },
        }
        return FakeHttpResponse(200, json.dumps(payload))


TOKEN_ENDPOINT = "https://keycloak.invalid/realms/acme/protocol/openid-connect/token"
GATEWAY_BASE_URL = "https://api.invalid"
CLIENT_ID = "ga-acme"
CLIENT_SECRET = "s3cr3t-not-a-real-value"  # pragma: allowlist secret


@pytest.fixture
def fake_transport() -> FakeGatewayTransport:
    return FakeGatewayTransport(
        token_endpoint=TOKEN_ENDPOINT,
        gateway_base_url=GATEWAY_BASE_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
