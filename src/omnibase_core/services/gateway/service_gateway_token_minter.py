# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ServiceGatewayTokenMinter — credential -> gateway JWT (OMN-15922).

One ``client_credentials`` grant against the tenant realm's token endpoint,
one audience assertion, one in-memory cache. Deliberately no ``refresh_token``
path: RFC 6749 §4.4.3 says the client-credentials grant SHOULD NOT issue one,
and Keycloak does not -- so "refresh" here means re-grant, which is also
exactly what the gateway's RE_ATTACH renewal mode assumes its clients do.

WHAT THE AUDIENCE CHECK IS, AND IS NOT
    It is NOT a security control. This client verifies no signature and holds
    no JWKS; the gateway does that (``service_keycloak_token_validator`` on the
    node, ``gateway_auth.py`` at the edge). A forged token would sail past this
    check and die at the gateway, which is the correct place for it to die.

    It IS a fail-fast against a live, specific, already-observed defect: the
    P0B per-tenant provisioner stamps only ``aud=redpanda-events``
    (``keycloak_client_manager.py`` BROKER_TOKEN_AUDIENCE), while attach
    requires exact set equality with ``{"gateway-attach"}``. Without this
    check, a correctly-configured operator with a genuinely broken credential
    sees an opaque 401 from a remote service several calls downstream. With
    it, they see which audience they got and which was needed, at the mint.

    The comparison is SET EQUALITY, mirroring the gateway rather than being
    merely compatible with it. A superset (a dual-audience broker+attach token)
    is rejected there and so is rejected here -- a client that accepted more
    than the gateway does would report success and then fail on the wire.

CACHING
    In memory, per instance, re-granted once ``now`` reaches ``exp - skew``.
    Not written to disk: a cached bearer on disk is a credential at rest with
    none of the protections the actual credential file gets, in exchange for
    saving one sub-second grant per process.
"""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime, timedelta
from typing import Final

from pydantic import SecretStr

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gateway.model_gateway_access_token import (
    ModelGatewayAccessToken,
)
from omnibase_core.models.gateway.model_gateway_credential import ModelGatewayCredential
from omnibase_core.protocols.http.protocol_gateway_transport import (
    ProtocolGatewayTransport,
)

__all__ = ["GATEWAY_ATTACH_AUDIENCES", "ServiceGatewayTokenMinter"]

# Exact audience set the gateway requires, mirrored from
# node_gateway_attach_effect/contract.yaml (required_audience: gateway-attach)
# and onex-api gateway_auth.GATEWAY_EXPECTED_AUDIENCES. A contract term, not a
# deployment knob -- which is why it is a constant here rather than config.
GATEWAY_ATTACH_AUDIENCES: Final[frozenset[str]] = frozenset({"gateway-attach"})

# Re-grant this far ahead of exp. Sized to cover clock skew between this
# machine and Keycloak plus one in-flight request: a token that is valid when
# the request leaves and expired when the gateway validates it is the classic
# expiry-boundary defect, and it presents as an intermittent 401.
_DEFAULT_SKEW_SECONDS: Final[int] = 30


class ServiceGatewayTokenMinter:
    """Mints and caches gateway access tokens for one credential."""

    def __init__(
        self,
        *,
        transport: ProtocolGatewayTransport,
        credential: ModelGatewayCredential,
        skew_seconds: int = _DEFAULT_SKEW_SECONDS,
    ) -> None:
        self._transport = transport
        self._credential = credential
        self._skew = timedelta(seconds=skew_seconds)
        self._cached: ModelGatewayAccessToken | None = None

    async def token_for(
        self, *, now: datetime, force_refresh: bool = False
    ) -> ModelGatewayAccessToken:
        """Return a token valid at ``now``, re-granting if inside the skew window.

        Args:
            now: Caller-supplied instant. Injected rather than read from the
                clock so the boundary cases are driven directly by tests.
            force_refresh: Skip the cache and grant unconditionally. Used by the
                attach path, where a still-valid-but-short token is not good
                enough: the gateway stamps a session's ``expires_at`` from
                ``min(token exp, max_session_ttl_seconds)``, so attaching with a
                token that has two minutes left buys a two-minute session. That
                is exactly the state the renewal cycle is trying to leave, so
                renewing into it would loop.

        Returns:
            A token whose ``expires_at`` is at least ``skew`` beyond ``now``.

        Raises:
            ModelOnexError: If the grant fails, the response is malformed, or
                the audience is not exactly the gateway-attach set.
        """
        cached = self._cached
        if (
            not force_refresh
            and cached is not None
            and now < cached.expires_at - self._skew
        ):
            return cached
        minted = await self._grant(now=now)
        self._cached = minted
        return minted

    async def _grant(self, *, now: datetime) -> ModelGatewayAccessToken:
        response = await self._transport.post_form(
            self._credential.token_endpoint,
            form={
                "grant_type": "client_credentials",
                "client_id": self._credential.client_id,
                "client_secret": self._credential.client_secret.get_secret_value(),
            },
            headers={"Accept": "application/json"},
        )
        if response.status != 200:
            # The body is NOT echoed: an OAuth2 error response is attacker- and
            # proxy-influenced, and an error path that pastes a remote body into
            # a local message is how secrets and tokens reach logs.
            raise ModelOnexError(
                "gateway token grant rejected by "
                f"{self._credential.token_endpoint} (HTTP {response.status}) for "
                f"client_id '{self._credential.client_id}'. Check the credential "
                "with 'onex auth status', or re-run 'onex auth login' with a "
                "freshly rotated secret.",
                error_code=EnumCoreErrorCode.AUTHENTICATION_ERROR,
            )

        payload = self._decode_json_object(
            await response.text(), source=self._credential.token_endpoint
        )
        access_token = self._require_string(payload, "access_token")
        expires_in = self._require_int(payload, "expires_in")
        audiences = self._audiences_of(access_token)

        if audiences != GATEWAY_ATTACH_AUDIENCES:
            raise ModelOnexError(
                "minted token carries audience "
                f"{sorted(audiences)} but the gateway requires exactly "
                f"{sorted(GATEWAY_ATTACH_AUDIENCES)} (set equality, not "
                f"membership). The Keycloak client '{self._credential.client_id}' "
                "needs an audience mapper stamping 'gateway-attach'.",
                error_code=EnumCoreErrorCode.AUTHENTICATION_ERROR,
            )

        return ModelGatewayAccessToken(
            access_token=SecretStr(access_token),
            expires_at=now + timedelta(seconds=expires_in),
            audiences=audiences,
        )

    # -- parsing -----------------------------------------------------------

    def _audiences_of(self, access_token: str) -> frozenset[str]:
        """Normalise the ``aud`` claim to a set, mirroring the gateway.

        RFC 7519 §4.1.3 permits ``aud`` to be a single case-sensitive string OR
        an array of them, and Keycloak switches to the array form the moment a
        client carries more than one audience mapper. Multiplicity and order
        must therefore not be observable -- ``aud`` is a set.
        """
        segments = access_token.split(".")
        if len(segments) != 3:
            raise ModelOnexError(
                "the token endpoint returned an access_token that is not a JWT "
                f"(expected 3 dot-separated segments, found {len(segments)}).",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            )
        padding = "=" * (-len(segments[1]) % 4)
        try:
            claims_bytes = base64.urlsafe_b64decode(segments[1] + padding)
        except (binascii.Error, ValueError) as exc:
            raise ModelOnexError(
                "the access_token's claims segment is not valid base64url.",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            ) from exc

        claims = self._decode_json_object(
            claims_bytes.decode("utf-8", errors="replace"),
            source="access_token claims",
        )
        raw = claims.get("aud")
        if isinstance(raw, str):
            return frozenset({raw})
        if isinstance(raw, list):
            if not all(isinstance(entry, str) for entry in raw):
                raise ModelOnexError(
                    "the access_token's 'aud' claim is a list containing "
                    "non-string entries.",
                    error_code=EnumCoreErrorCode.PARSING_ERROR,
                )
            return frozenset(str(entry) for entry in raw)
        raise ModelOnexError(
            "the access_token carries no usable 'aud' claim; the gateway "
            "requires exactly "
            f"{sorted(GATEWAY_ATTACH_AUDIENCES)}.",
            error_code=EnumCoreErrorCode.AUTHENTICATION_ERROR,
        )

    def _decode_json_object(self, raw: str, *, source: str) -> dict[str, object]:
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ModelOnexError(
                f"{source} returned a body that is not valid JSON.",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            ) from exc
        if not isinstance(document, dict):
            raise ModelOnexError(
                f"{source} returned {type(document).__name__}, expected a JSON object.",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            )
        return {str(key): value for key, value in document.items()}

    def _require_string(self, payload: dict[str, object], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ModelOnexError(
                f"the token endpoint response has no usable '{key}' field.",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            )
        return value

    def _require_int(self, payload: dict[str, object], key: str) -> int:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ModelOnexError(
                f"the token endpoint response has no usable '{key}' field.",
                error_code=EnumCoreErrorCode.PARSING_ERROR,
            )
        return value

    @staticmethod
    def utc_now() -> datetime:
        """The clock, in one named place, so callers do not each pick one."""
        return datetime.now(UTC)
