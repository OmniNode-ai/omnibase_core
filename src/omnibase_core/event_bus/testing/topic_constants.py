# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Topic name constants for the shared ``event_bus_substrate`` contract tests.

These are TEST-FIXTURE topics -- synthetic names the shared contract tests
(``contract_event_bus_substrate.py``) publish/subscribe to. They are not
real production ONEX events and are not registered in
``constants_event_types.py`` (the canonical production event-type registry)
for that reason; this module exists solely so the topic literals live in an
approved constants file (basename allowlisted by the ``check-hardcoded-topics``
pre-commit hook) rather than inline in test bodies.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from typing import Final

SEAM_TEST_TOPIC: Final[str] = (
    "onex.evt.omnibase-infra.event-bus-substrate-seam-test.v1"  # env-var-ok: topic name constant, not configuration
)
FIDELITY_JOIN_LEAVE_TOPIC: Final[str] = (
    "onex.evt.omnibase-infra.fidelity-join-leave.v1"  # env-var-ok: topic name constant, not configuration
)
FIDELITY_EARLIEST_TOPIC: Final[str] = (
    "onex.evt.omnibase-infra.fidelity-earliest.v1"  # env-var-ok: topic name constant, not configuration
)
FIDELITY_LATEST_TOPIC: Final[str] = (
    "onex.evt.omnibase-infra.fidelity-latest.v1"  # env-var-ok: topic name constant, not configuration
)
FIDELITY_REJOIN_TOPIC: Final[str] = (
    "onex.evt.omnibase-infra.fidelity-rejoin.v1"  # env-var-ok: topic name constant, not configuration
)
FIDELITY_REBALANCE_TOPIC: Final[str] = (
    "onex.evt.omnibase-infra.fidelity-rebalance.v1"  # env-var-ok: topic name constant, not configuration
)

__all__: list[str] = [
    "FIDELITY_EARLIEST_TOPIC",
    "FIDELITY_JOIN_LEAVE_TOPIC",
    "FIDELITY_LATEST_TOPIC",
    "FIDELITY_REBALANCE_TOPIC",
    "FIDELITY_REJOIN_TOPIC",
    "SEAM_TEST_TOPIC",
]
