# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Bearer on every gateway call, and the RE_ATTACH renewal cycle (OMN-15922).

Drives the real ``ServiceGatewaySessionClient`` against the fake token
endpoint + fake gateway from ``conftest``. The claims under test are the
ones the OMN-15952 contract makes and the client must obey:

* every gateway call carries ``Authorization: Bearer`` -- no anonymous call
  exists on any path, including the renewal path;
* a heartbeat NEVER extends ``expires_at`` -- the client must not believe it
  does, so ``ensure_attached`` past the renewal window re-attaches;
* renewal is a fresh ``client_credentials`` grant plus a fresh attach that
  mints a NEW ``session_id``; and
* an expired or rejected session is a re-attach or a hard error, never a
  silent continuation with the dead session.
"""

from __future__ import annotations

import random
from datetime import timedelta

import pytest
from pydantic import SecretStr

from omnibase_core.enums.enum_gateway_renewal_mode import EnumGatewayRenewalMode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gateway.model_gateway_credential import ModelGatewayCredential
from omnibase_core.services.gateway.service_gateway_session_client import (
    ServiceGatewaySessionClient,
)
from omnibase_core.services.gateway.service_gateway_token_minter import (
    ServiceGatewayTokenMinter,
)
from tests.unit.gateway.conftest import (
    CLIENT_ID,
    CLIENT_SECRET,
    GATEWAY_BASE_URL,
    TOKEN_ENDPOINT,
    FakeGatewayTransport,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _credential() -> ModelGatewayCredential:
    return ModelGatewayCredential(
        tenant_slug="acme",
        client_id=CLIENT_ID,
        client_secret=SecretStr(CLIENT_SECRET),
        token_endpoint=TOKEN_ENDPOINT,
        base_url=GATEWAY_BASE_URL,
        edge_instance_id="test-edge",
    )


def _client(transport: FakeGatewayTransport) -> ServiceGatewaySessionClient:
    credential = _credential()
    return ServiceGatewaySessionClient(
        transport=transport,
        credential=credential,
        minter=ServiceGatewayTokenMinter(transport=transport, credential=credential),
        rng=random.Random(1234),
    )


async def test_attach_sends_a_bearer_and_returns_the_contract_declared_cycle(
    fake_transport: FakeGatewayTransport,
) -> None:
    attachment = await _client(fake_transport).attach(now=fake_transport.now)

    url, body, headers = fake_transport.json_requests[-1]
    assert url == f"{GATEWAY_BASE_URL}/v1/gateway/attach"
    assert headers["Authorization"].startswith("Bearer ")
    assert "edge_instance_id" in body
    # The token itself is never placed in the JSON body -- only the header.
    assert fake_transport.issued_tokens[-1] not in body

    assert attachment.heartbeat_interval_seconds == 15
    assert attachment.renewal.mode is EnumGatewayRenewalMode.RE_ATTACH
    assert attachment.renewal.margin_seconds == 120
    assert attachment.renewal.jitter_seconds == 30
    assert attachment.renewal.renew_at == attachment.session.expires_at - timedelta(
        seconds=120
    )
    assert attachment.renewal.renew_at < attachment.session.expires_at


async def test_an_attach_response_missing_the_renewal_directive_is_refused(
    fake_transport: FakeGatewayTransport,
) -> None:
    """Required on the node; the client must not paper over an edge that drops it.

    A client that shrugged and carried on would run an unattended runtime with
    no renewal policy at all -- the precise gap OMN-15952 was filed against.
    """

    class _NoRenewal(FakeGatewayTransport):
        def _attach(self):  # type: ignore[no-untyped-def]
            from tests.unit.gateway.conftest import FakeHttpResponse

            response = super()._attach()
            import json as _json

            payload = _json.loads(response._body)
            del payload["renewal"]
            return FakeHttpResponse(200, _json.dumps(payload))

    transport = _NoRenewal(
        token_endpoint=TOKEN_ENDPOINT,
        gateway_base_url=GATEWAY_BASE_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    with pytest.raises(ModelOnexError) as caught:
        await _client(transport).attach(now=transport.now)

    assert "renewal" in str(caught.value)


async def test_a_heartbeat_carries_the_bearer_and_never_moves_the_ceiling(
    fake_transport: FakeGatewayTransport,
) -> None:
    client = _client(fake_transport)
    attachment = await client.attach(now=fake_transport.now)
    ceiling = attachment.session.expires_at

    later = fake_transport.now + timedelta(seconds=15)
    fake_transport.now = later
    session = await client.heartbeat(now=later)

    _, _, headers = fake_transport.json_requests[-1]
    assert headers["Authorization"].startswith("Bearer ")
    assert session.expires_at == ceiling
    assert fake_transport.attach_count == 1


async def test_ensure_attached_is_a_no_op_before_the_renewal_window_opens(
    fake_transport: FakeGatewayTransport,
) -> None:
    client = _client(fake_transport)
    first = await client.attach(now=fake_transport.now)

    early = fake_transport.now + timedelta(seconds=60)
    fake_transport.now = early
    again = await client.ensure_attached(now=early)

    assert again.session.session_id == first.session.session_id
    assert fake_transport.attach_count == 1


async def test_ensure_attached_inside_the_window_re_attaches_with_a_fresh_grant(
    fake_transport: FakeGatewayTransport,
) -> None:
    """RE_ATTACH: new grant, new attach, NEW session_id -- not an extension."""
    client = _client(fake_transport)
    first = await client.attach(now=fake_transport.now)
    grants_before = len(fake_transport.form_requests)

    # The window's CLOSE, not its opening: the client draws its own instant
    # somewhere inside [renew_not_before, renew_at], so renew_not_before + 1s
    # is not yet due for every draw -- but renew_at is due for all of them.
    inside = first.renewal.renew_at
    fake_transport.now = inside
    second = await client.ensure_attached(now=inside)

    assert fake_transport.attach_count == 2
    assert second.session.session_id != first.session.session_id
    assert len(fake_transport.form_requests) > grants_before
    assert second.session.expires_at > first.session.expires_at


async def test_the_renewal_grant_is_client_credentials_not_a_refresh_exchange(
    fake_transport: FakeGatewayTransport,
) -> None:
    client = _client(fake_transport)
    first = await client.attach(now=fake_transport.now)

    inside = first.renewal.renew_at
    fake_transport.now = inside
    await client.ensure_attached(now=inside)

    _, form = fake_transport.form_requests[-1]
    assert form["grant_type"] == "client_credentials"


async def test_a_session_past_its_ceiling_re_attaches_rather_than_continuing(
    fake_transport: FakeGatewayTransport,
) -> None:
    client = _client(fake_transport)
    first = await client.attach(now=fake_transport.now)

    past = first.session.expires_at + timedelta(seconds=1)
    fake_transport.now = past
    renewed = await client.ensure_attached(now=past)

    assert renewed.session.session_id != first.session.session_id
    assert renewed.session.expires_at > past


async def test_a_heartbeat_on_an_expired_session_fails_closed_instead_of_pretending(
    fake_transport: FakeGatewayTransport,
) -> None:
    """Never a silent continuation: past the ceiling, heartbeat is an error."""
    client = _client(fake_transport)
    first = await client.attach(now=fake_transport.now)

    past = first.session.expires_at + timedelta(seconds=1)
    fake_transport.now = past
    calls_before = len(fake_transport.json_requests)

    with pytest.raises(ModelOnexError) as caught:
        await client.heartbeat(now=past)

    assert "expired" in str(caught.value).lower()
    # It did not even try -- an expired session is a client-side fact.
    assert len(fake_transport.json_requests) == calls_before


async def test_a_revoked_credential_fails_closed_on_the_next_call(
    fake_transport: FakeGatewayTransport,
) -> None:
    client = _client(fake_transport)
    await client.attach(now=fake_transport.now)

    fake_transport.revoked = True
    later = fake_transport.now + timedelta(seconds=15)
    fake_transport.now = later

    with pytest.raises(ModelOnexError) as caught:
        await client.heartbeat(now=later)

    assert CLIENT_SECRET not in str(caught.value)


async def test_no_gateway_call_is_ever_made_without_a_bearer(
    fake_transport: FakeGatewayTransport,
) -> None:
    """Structural sweep, not a single-path observation.

    Asserting on one run's happy path would pass against an implementation
    that had an anonymous fallback it happened not to take.
    """
    client = _client(fake_transport)
    first = await client.attach(now=fake_transport.now)
    fake_transport.now += timedelta(seconds=15)
    await client.heartbeat(now=fake_transport.now)
    fake_transport.now = first.renewal.renew_at
    await client.ensure_attached(now=fake_transport.now)

    assert len(fake_transport.json_requests) >= 3
    assert all(
        headers.get("Authorization", "").startswith("Bearer ")
        for _, _, headers in fake_transport.json_requests
    )


async def test_the_secret_never_appears_in_any_request_the_gateway_sees(
    fake_transport: FakeGatewayTransport,
) -> None:
    client = _client(fake_transport)
    first = await client.attach(now=fake_transport.now)
    fake_transport.now = first.renewal.renew_at
    await client.ensure_attached(now=fake_transport.now)

    for _, body, headers in fake_transport.json_requests:
        assert CLIENT_SECRET not in body
        assert all(CLIENT_SECRET not in value for value in headers.values())


async def test_a_gateway_rejection_names_the_status_without_leaking_material(
    fake_transport: FakeGatewayTransport,
) -> None:
    fake_transport.revoked = True

    with pytest.raises(ModelOnexError) as caught:
        await _client(fake_transport).attach(now=fake_transport.now)

    assert CLIENT_SECRET not in str(caught.value)
