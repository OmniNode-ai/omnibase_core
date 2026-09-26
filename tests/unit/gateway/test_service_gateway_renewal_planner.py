# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Client half of the OMN-15952 renewal cycle (OMN-15922).

The server computes the window and hands it over on the attach response
(``ModelGatewayRenewalDirective``: mode RE_ATTACH, ``renew_not_before <=
renew_at < session_expires_at``, ``margin_seconds`` 120 /
``jitter_seconds`` 30 from ``node_gateway_attach_effect/contract.yaml``).
The client's job is narrow and entirely testable without a clock: pick one
instant inside the window, know when that instant has passed, and refuse a
directive whose window it cannot honour.

The jitter draw takes an injected ``random.Random`` precisely so the
"uniform inside the window" claim is provable rather than asserted -- a
decorrelation window that silently always yields its own left edge would
re-synchronise a fleet while every ordering assertion still passed.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest

from omnibase_core.enums.enum_gateway_renewal_mode import EnumGatewayRenewalMode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gateway.model_gateway_renewal_directive import (
    ModelGatewayRenewalDirective,
)
from omnibase_core.services.gateway.service_gateway_renewal_planner import (
    ServiceGatewayRenewalPlanner,
)

pytestmark = pytest.mark.unit

_ATTACHED_AT = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)


def _directive(
    *,
    ttl_seconds: int = 900,
    margin_seconds: int = 120,
    jitter_seconds: int = 30,
) -> ModelGatewayRenewalDirective:
    expires = _ATTACHED_AT + timedelta(seconds=ttl_seconds)
    renew_at = expires - timedelta(seconds=margin_seconds)
    return ModelGatewayRenewalDirective(
        mode=EnumGatewayRenewalMode.RE_ATTACH,
        session_expires_at=expires,
        renew_not_before=renew_at - timedelta(seconds=jitter_seconds),
        renew_at=renew_at,
        margin_seconds=margin_seconds,
        jitter_seconds=jitter_seconds,
    )


def test_the_only_renewal_mode_the_client_understands_is_re_attach() -> None:
    """A second member would mean a client that guesses; there is none."""
    assert [member.value for member in EnumGatewayRenewalMode] == ["RE_ATTACH"]


def test_a_directive_that_renews_at_or_after_expiry_cannot_be_constructed() -> None:
    """Mirrors the model-level invariant the node enforces on the wire."""
    expires = _ATTACHED_AT + timedelta(seconds=900)
    with pytest.raises(ValueError):
        ModelGatewayRenewalDirective(
            mode=EnumGatewayRenewalMode.RE_ATTACH,
            session_expires_at=expires,
            renew_not_before=expires,
            renew_at=expires,
            margin_seconds=120,
            jitter_seconds=30,
        )


def test_a_directive_whose_window_opens_after_it_closes_cannot_be_constructed() -> None:
    expires = _ATTACHED_AT + timedelta(seconds=900)
    renew_at = expires - timedelta(seconds=120)
    with pytest.raises(ValueError):
        ModelGatewayRenewalDirective(
            mode=EnumGatewayRenewalMode.RE_ATTACH,
            session_expires_at=expires,
            renew_not_before=renew_at + timedelta(seconds=1),
            renew_at=renew_at,
            margin_seconds=120,
            jitter_seconds=30,
        )


def test_every_planned_instant_lands_inside_the_declared_window() -> None:
    directive = _directive()
    planner = ServiceGatewayRenewalPlanner()

    instants = [
        planner.plan_instant(directive, rng=random.Random(seed)) for seed in range(200)
    ]

    assert all(
        directive.renew_not_before <= instant <= directive.renew_at
        for instant in instants
    )


def test_the_jitter_draw_actually_spreads_rather_than_collapsing_to_an_edge() -> None:
    """A fleet that all picks ``renew_not_before`` is a fleet with no jitter."""
    directive = _directive()
    planner = ServiceGatewayRenewalPlanner()

    instants = {
        planner.plan_instant(directive, rng=random.Random(seed)) for seed in range(200)
    }

    assert len(instants) > 1
    assert instants != {directive.renew_not_before}
    assert instants != {directive.renew_at}


def test_the_planned_instant_is_deterministic_for_a_given_generator_state() -> None:
    directive = _directive()
    planner = ServiceGatewayRenewalPlanner()

    first = planner.plan_instant(directive, rng=random.Random(7))
    second = planner.plan_instant(directive, rng=random.Random(7))

    assert first == second


def test_renewal_is_due_from_the_instant_the_window_opens() -> None:
    """Erring early costs one token; erring late costs the session."""
    directive = _directive()
    planner = ServiceGatewayRenewalPlanner()

    assert not planner.is_renewal_due(
        directive, now=directive.renew_not_before - timedelta(seconds=1)
    )
    assert planner.is_renewal_due(directive, now=directive.renew_not_before)
    assert planner.is_renewal_due(directive, now=directive.renew_at)
    assert planner.is_renewal_due(directive, now=directive.session_expires_at)


def test_a_window_the_client_cannot_honour_is_reported_rather_than_silently_run() -> (
    None
):
    """Margin shorter than the client's own round trip is a real deployment.

    Refusing loudly beats renewing at an instant that has already passed by
    the time the grant returns -- the classic expiry-boundary defect.
    """
    directive = _directive(ttl_seconds=90, margin_seconds=60, jitter_seconds=0)
    planner = ServiceGatewayRenewalPlanner()

    with pytest.raises(ModelOnexError) as caught:
        planner.assert_window_is_honourable(
            directive,
            now=directive.renew_at + timedelta(seconds=1),
            minimum_lead_seconds=30,
        )

    assert "renew" in str(caught.value).lower()


def test_a_window_with_adequate_lead_is_accepted() -> None:
    directive = _directive()
    planner = ServiceGatewayRenewalPlanner()

    planner.assert_window_is_honourable(
        directive, now=_ATTACHED_AT, minimum_lead_seconds=30
    )


def test_the_contract_defaults_are_the_ones_the_node_declares() -> None:
    """120s margin / 30s jitter, read off node_gateway_attach_effect 0.3.0."""
    directive = _directive()

    assert directive.margin_seconds == 120
    assert directive.jitter_seconds == 30
    assert directive.renew_at == directive.session_expires_at - timedelta(seconds=120)
    assert directive.renew_not_before == directive.renew_at - timedelta(seconds=30)
