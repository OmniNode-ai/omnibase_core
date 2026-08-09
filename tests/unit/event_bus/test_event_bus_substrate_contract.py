# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Collects the shared ``event_bus_substrate`` contract tests (OMN-15789).

The actual test bodies live in
``omnibase_core.event_bus.testing.contract_event_bus_substrate`` so
``omnibase_infra`` can import and re-run the identical functions against its
own extended (``+real_broker``) fixtures without duplicating any assertion
logic -- see that module's docstring for the full rationale (AC3, AC6).

Star-importing them here is what makes pytest collect them as part of THIS
repo's test suite, resolved against the ``event_bus_substrate`` /
``fidelity_event_bus_substrate`` fixtures registered in this package's
``conftest.py`` (2 core-resident params; no Kafka dependency).
"""

from __future__ import annotations

from omnibase_core.event_bus.testing.contract_event_bus_substrate import (  # noqa: F401
    test_auto_offset_reset_earliest_replays_retained_history,
    test_auto_offset_reset_latest_delivers_only_future_messages,
    test_group_join_gates_delivery_only_while_joined,
    test_publish_subscribe_seam_matches_real_consumer_group_derivation,
    test_rebalance_window_drops_uncommitted_inflight_message,
    test_rejoin_resumes_from_committed_offset_ignoring_auto_offset_reset,
)
