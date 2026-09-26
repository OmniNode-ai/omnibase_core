# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ServiceGatewayRenewalPlanner — the client half of the RE_ATTACH cycle (OMN-15922).

The server computes the window and hands it over on the attach response
(OMN-15952, ``service_gateway_renewal_policy`` on the node). This class does
not recompute it -- recomputing would make the client a second authority over
a term the contract already settled, and the two would drift the first time the
node's ``renewal_margin_seconds`` changed. It reads the directive and answers
three questions about it:

  * ``plan_instant``  -- which moment inside the jitter window is mine?
  * ``is_renewal_due`` -- has that window opened?
  * ``assert_window_is_honourable`` -- can I still make it?

Every method is pure: ``now`` and the random generator are both injected. That
is what makes the boundary cases (a token whose whole life is shorter than the
margin, an instant exactly at ``renew_not_before``) driveable by tests rather
than sleepable-through.

WHY THE JITTER DRAW IS AN INJECTED GENERATOR
    A fleet provisioned in one bootstrap batch shares an attach instant, so
    without spreading it shares a renewal instant -- and the synchronisation is
    self-sustaining, because a batch that renews together stays together.
    Taking a ``random.Random`` rather than calling the module-level ``random``
    lets a test prove the draw actually spreads, instead of asserting only that
    each individual result is inside the window (which a constant would satisfy).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.gateway.model_gateway_renewal_directive import (
    ModelGatewayRenewalDirective,
)

__all__ = ["ServiceGatewayRenewalPlanner"]


class ServiceGatewayRenewalPlanner:
    """Reads a server-issued renewal directive and schedules against it."""

    def plan_instant(
        self,
        directive: ModelGatewayRenewalDirective,
        *,
        rng: random.Random,
    ) -> datetime:
        """Pick this client's own renewal moment, uniform inside the window.

        Args:
            directive: The cycle the gateway declared at attach.
            rng: Generator for the decorrelation draw.

        Returns:
            An instant in ``[renew_not_before, renew_at]``. A zero-width window
            (``jitter_seconds`` 0, or a floor collision on a very short-lived
            session) collapses to that single instant rather than erroring --
            no spreading is a legitimate configuration, not a failure.
        """
        window = (directive.renew_at - directive.renew_not_before).total_seconds()
        if window <= 0:
            return directive.renew_at
        return directive.renew_not_before + timedelta(seconds=rng.random() * window)

    def is_renewal_due(
        self,
        directive: ModelGatewayRenewalDirective,
        *,
        now: datetime,
    ) -> bool:
        """True once ``now`` has reached the window's opening edge.

        Inclusive at ``renew_not_before``: at the instant the window opens,
        renewal is due. Erring early costs one extra token; erring late costs
        the session.
        """
        return now >= directive.renew_not_before

    def assert_window_is_honourable(
        self,
        directive: ModelGatewayRenewalDirective,
        *,
        now: datetime,
        minimum_lead_seconds: int,
    ) -> None:
        """Refuse a window this client can no longer complete inside.

        A margin shorter than the client's own round trip is a real deployment
        (a short token lifespan, a margin tuned down, a machine that slept).
        Running the cycle anyway means re-granting at an instant that has
        already passed by the time the grant returns, which presents as an
        intermittent 401 rather than as the configuration problem it is.

        Args:
            directive: The cycle the gateway declared.
            now: Current instant.
            minimum_lead_seconds: Time this client needs for grant + attach.

        Raises:
            ModelOnexError: When less than ``minimum_lead_seconds`` remains
                before ``renew_at``.
        """
        remaining = (directive.renew_at - now).total_seconds()
        if remaining < minimum_lead_seconds:
            raise ModelOnexError(
                "gateway renewal window cannot be honoured: renew_at is "
                f"{remaining:.0f}s away but this client needs "
                f"{minimum_lead_seconds}s for a re-grant plus re-attach "
                f"(session_expires_at {directive.session_expires_at.isoformat()}, "
                f"margin {directive.margin_seconds}s). Re-attach now, or raise "
                "the gateway's renewal_margin_seconds.",
                error_code=EnumCoreErrorCode.TIMEOUT_EXCEEDED,
            )
