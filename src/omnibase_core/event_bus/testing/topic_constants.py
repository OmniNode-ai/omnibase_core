# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Topic name constants for the shared ``event_bus_substrate`` contract tests.

These are TEST-FIXTURE topics -- synthetic names the shared contract tests
(``contract_event_bus_substrate.py``) publish/subscribe to. They are not
real production ONEX events and are not registered in
``constants_event_types.py`` (the canonical production event-type registry)
for that reason; the topic names are declared in ``substrate_test_topics.yaml``
beside this module, not inline in test bodies.

.. versionadded:: OMN-15789
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import TypeAdapter
from ruamel.yaml import YAML

with (Path(__file__).parent / "substrate_test_topics.yaml").open(
    encoding="utf-8"
) as _contract:
    _TOPICS = TypeAdapter(dict[str, str]).validate_python(
        YAML(typ="safe").load(_contract)["topics"]
    )

SEAM_TEST_TOPIC: Final[str] = _TOPICS["seam_test"]
FIDELITY_JOIN_LEAVE_TOPIC: Final[str] = _TOPICS["fidelity_join_leave"]
FIDELITY_EARLIEST_TOPIC: Final[str] = _TOPICS["fidelity_earliest"]
FIDELITY_LATEST_TOPIC: Final[str] = _TOPICS["fidelity_latest"]
FIDELITY_REJOIN_TOPIC: Final[str] = _TOPICS["fidelity_rejoin"]
FIDELITY_REBALANCE_TOPIC: Final[str] = _TOPICS["fidelity_rebalance"]

__all__: list[str] = [
    "FIDELITY_EARLIEST_TOPIC",
    "FIDELITY_JOIN_LEAVE_TOPIC",
    "FIDELITY_LATEST_TOPIC",
    "FIDELITY_REBALANCE_TOPIC",
    "FIDELITY_REJOIN_TOPIC",
    "SEAM_TEST_TOPIC",
]
