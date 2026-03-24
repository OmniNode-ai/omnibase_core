# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Test that COMPUTE contracts have no event fields (pure nodes)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RESOLVE_CONTRACT = (
    Path(__file__).parent.parent.parent.parent
    / "src/omnibase_core/nodes/node_contract_resolve_compute/contract.yaml"
)


@pytest.mark.unit
def test_compute_contract_has_no_event_fields() -> None:
    """COMPUTE nodes must be pure -- no consumed_events or produced_events."""
    with open(RESOLVE_CONTRACT) as f:
        contract = yaml.safe_load(f)
    assert "consumed_events" not in contract, (
        "COMPUTE contract must not declare consumed_events"
    )
    assert "produced_events" not in contract, (
        "COMPUTE contract must not declare produced_events"
    )
