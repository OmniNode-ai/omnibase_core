# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the import-layering growth ratchet (OMN-14340, epic OMN-3210).

Verifies that the live omnibase_core import graph introduces no NEW frozen-family
edge beyond the committed baseline, that the headline protocols->models number
stays frozen at 65, and that the ratchet actually hard-fails on synthetic growth
(so the enforcement can't silently rot into a no-op).
"""

from __future__ import annotations

import pytest

from scripts.ci.check_import_ratchet import (
    FROZEN_PROTOCOLS_MODELS_MAX,
    HUBS,
    EdgeSets,
    compute_current_edges,
    find_violations,
    load_baseline,
)


@pytest.fixture(scope="module")
def current() -> EdgeSets:
    """Live protocols->models + hub-inbound edge sets (grimp; built once)."""
    return compute_current_edges()


@pytest.fixture(scope="module")
def baseline() -> EdgeSets:
    return load_baseline()


def test_no_new_forbidden_edges(current: EdgeSets, baseline: EdgeSets) -> None:
    """The live graph adds no edge/importer outside the frozen baseline."""
    violations = find_violations(current, baseline)
    assert violations == {}, (
        "Import-layering growth ratchet violated — new frozen-family edge(s):\n"
        + "\n".join(f"  {k}: {v}" for k, v in violations.items())
    )


def test_headline_protocols_models_number_frozen() -> None:
    """The 'no permanent exception' number is locked; lowering it is a visible edit."""
    assert FROZEN_PROTOCOLS_MODELS_MAX == 65


def test_current_protocols_models_within_ceiling(current: EdgeSets) -> None:
    """protocols->models is monotonically non-increasing (may shrink, never grow)."""
    assert len(current["protocols_to_models"]) <= FROZEN_PROTOCOLS_MODELS_MAX


def test_baseline_protocols_models_frozen_at_65(baseline: EdgeSets) -> None:
    """The committed baseline pins protocols->models at exactly the frozen count."""
    assert len(baseline["protocols_to_models"]) == FROZEN_PROTOCOLS_MODELS_MAX


def test_baseline_covers_all_hubs(baseline: EdgeSets) -> None:
    for hub in HUBS:
        assert hub in baseline["hub_inbound"], f"hub '{hub}' missing from baseline"


def test_ratchet_flags_new_protocols_models_edge(
    current: EdgeSets, baseline: EdgeSets
) -> None:
    """Synthetic proof: a net-new protocols->models edge is caught (not a no-op)."""
    injected: EdgeSets = {
        "protocols_to_models": [
            *current["protocols_to_models"],
            "omnibase_core.protocols.protocol_synthetic_probe "
            "-> omnibase_core.models.synthetic_probe_model",
        ],
        "hub_inbound": current["hub_inbound"],
    }
    assert "protocols_to_models" in find_violations(injected, baseline)


@pytest.mark.parametrize("hub", HUBS)
def test_ratchet_flags_new_hub_importer(
    hub: str, current: EdgeSets, baseline: EdgeSets
) -> None:
    """Synthetic proof: a net-new importer into each hub is caught."""
    hub_inbound = {h: list(current["hub_inbound"][h]) for h in HUBS}
    hub_inbound[hub] = [*hub_inbound[hub], "omnibase_core.synthetic_probe.new_importer"]
    injected: EdgeSets = {
        "protocols_to_models": current["protocols_to_models"],
        "hub_inbound": hub_inbound,
    }
    assert f"hub:{hub}" in find_violations(injected, baseline)
