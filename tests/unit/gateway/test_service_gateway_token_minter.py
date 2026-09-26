# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""client_credentials mint + audience gate + re-grant skew (OMN-15922).

The audience assertion here is the client half of the seam the gateway
enforces server-side (``gateway_auth.py::_assert_exact_audience``, exact SET
equality against ``{"gateway-attach"}``, list- or string-valued ``aud``
normalised first). Mirroring it client-side does not make the client a
security authority -- it cannot, it verifies no signature -- it makes the
P0B audience defect (a real per-tenant token carrying only
``redpanda-events``) fail at the mint with a diagnosable message instead of
as an opaque 401 several calls later.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gateway.model_gateway_credential import ModelGatewayCredential
from omnibase_core.services.gateway.service_gateway_token_minter import (
    GATEWAY_ATTACH_AUDIENCES,
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


def _minter(transport: FakeGatewayTransport) -> ServiceGatewayTokenMinter:
    return ServiceGatewayTokenMinter(transport=transport, credential=_credential())


def test_the_contract_audience_set_is_exactly_gateway_attach() -> None:
    assert frozenset({"gateway-attach"}) == GATEWAY_ATTACH_AUDIENCES


async def test_a_client_credentials_grant_yields_a_token_with_the_declared_expiry(
    fake_transport: FakeGatewayTransport,
) -> None:
    token = await _minter(fake_transport).token_for(now=fake_transport.now)

    assert token.access_token.get_secret_value() == fake_transport.issued_tokens[-1]
    assert token.expires_at == fake_transport.now + timedelta(seconds=900)
    assert token.audiences == frozenset({"gateway-attach"})

    url, form = fake_transport.form_requests[-1]
    assert url == TOKEN_ENDPOINT
    assert form["grant_type"] == "client_credentials"
    assert "refresh_token" not in form


async def test_a_broker_only_audience_is_refused_before_the_token_is_ever_used(
    fake_transport: FakeGatewayTransport,
) -> None:
    """The live P0B defect: aud=redpanda-events and nothing else."""
    fake_transport.audiences = ["redpanda-events"]

    with pytest.raises(ModelOnexError) as caught:
        await _minter(fake_transport).token_for(now=fake_transport.now)

    message = str(caught.value)
    assert "gateway-attach" in message
    assert "redpanda-events" in message
    # Nothing was attempted against the gateway with a bad-audience token.
    assert fake_transport.json_requests == []


async def test_a_dual_audience_token_is_refused_because_the_check_is_set_equality(
    fake_transport: FakeGatewayTransport,
) -> None:
    """Superset is not "good enough" -- the gateway rejects it, so we do too."""
    fake_transport.audiences = ["gateway-attach", "redpanda-events"]

    with pytest.raises(ModelOnexError):
        await _minter(fake_transport).token_for(now=fake_transport.now)


async def test_a_string_valued_aud_claim_is_accepted_the_same_as_a_single_element_list(
    fake_transport: FakeGatewayTransport,
) -> None:
    """RFC 7519 4.1.3 permits both spellings; only the SET is observable."""
    fake_transport.audiences = ["gateway-attach"]
    single = await _minter(fake_transport).token_for(now=fake_transport.now)

    listed = FakeGatewayTransport(
        token_endpoint=TOKEN_ENDPOINT,
        gateway_base_url=GATEWAY_BASE_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        audiences=["gateway-attach", "gateway-attach"],
    )
    listed_token = await _minter(listed).token_for(now=listed.now)

    assert single.audiences == listed_token.audiences == frozenset({"gateway-attach"})


async def test_a_rejected_credential_fails_closed_and_never_echoes_the_secret(
    fake_transport: FakeGatewayTransport,
) -> None:
    fake_transport.token_endpoint_status = 401

    with pytest.raises(ModelOnexError) as caught:
        await _minter(fake_transport).token_for(now=fake_transport.now)

    assert CLIENT_SECRET not in str(caught.value)
    assert CLIENT_SECRET not in repr(caught.value)


async def test_a_cached_token_is_reused_until_it_enters_the_skew_window(
    fake_transport: FakeGatewayTransport,
) -> None:
    minter = _minter(fake_transport)
    start = fake_transport.now

    await minter.token_for(now=start)
    await minter.token_for(now=start + timedelta(seconds=600))
    assert len(fake_transport.form_requests) == 1

    # exp - skew: one grant per token lifetime, not one per call.
    inside_skew = start + timedelta(seconds=900) - timedelta(seconds=30)
    fake_transport.now = inside_skew
    await minter.token_for(now=inside_skew)
    assert len(fake_transport.form_requests) == 2


async def test_an_expired_cached_token_is_never_handed_back(
    fake_transport: FakeGatewayTransport,
) -> None:
    minter = _minter(fake_transport)
    start = fake_transport.now
    first = await minter.token_for(now=start)

    after_expiry = start + timedelta(seconds=1200)
    fake_transport.now = after_expiry
    second = await minter.token_for(now=after_expiry)

    assert (
        second.access_token.get_secret_value() != first.access_token.get_secret_value()
    )
    assert second.expires_at > after_expiry


async def test_the_grant_never_asks_for_a_refresh_token(
    fake_transport: FakeGatewayTransport,
) -> None:
    """client_credentials issues no refresh_token; renewal is re-grant."""
    await _minter(fake_transport).token_for(now=fake_transport.now)

    _, form = fake_transport.form_requests[-1]
    assert form["grant_type"] == "client_credentials"
    assert all("refresh" not in key for key in form)


async def test_a_malformed_token_response_refuses_rather_than_minting_nothing_useful(
    fake_transport: FakeGatewayTransport,
) -> None:
    class _Broken(FakeGatewayTransport):
        async def post_form(self, url: str, *, form: object, headers: object) -> object:  # type: ignore[override]
            from tests.unit.gateway.conftest import FakeHttpResponse

            return FakeHttpResponse(200, '{"token_type":"Bearer"}')

    broken = _Broken(
        token_endpoint=TOKEN_ENDPOINT,
        gateway_base_url=GATEWAY_BASE_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    with pytest.raises(ModelOnexError) as caught:
        await _minter(broken).token_for(now=datetime.now(UTC))

    assert "access_token" in str(caught.value)
