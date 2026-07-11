# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the import-layering growth ratchet (OMN-14340, epic OMN-3210).

Verifies that the live omnibase_core import graph introduces no NEW hard-fail
frozen-family edge beyond the committed baseline, that the headline
protocols->models number stays frozen at 65, that the tiered hub enforcement
holds (mixins/protocols hard-fail, utils warn-only), and that the ratchet
actually hard-fails on synthetic growth (so it can't rot into a no-op).
"""

from __future__ import annotations

import pytest

from scripts.ci.check_import_ratchet import (
    FROZEN_PROTOCOLS_MODELS_MAX,
    HARD_FAIL_HUBS,
    HUB_IMPORTER_RELOCATIONS,
    HUBS,
    WARN_HUBS,
    EdgeSets,
    compute_current_edges,
    find_violations,
    find_warnings,
    load_baseline,
)


@pytest.fixture(scope="module")
def current() -> EdgeSets:
    """Live protocols->models + hub-inbound edge sets (grimp; built once)."""
    return compute_current_edges()


@pytest.fixture(scope="module")
def baseline() -> EdgeSets:
    return load_baseline()


def _inject_hub_importer(current: EdgeSets, hub: str) -> EdgeSets:
    hub_inbound = {h: list(current["hub_inbound"][h]) for h in HUBS}
    hub_inbound[hub] = [*hub_inbound[hub], "omnibase_core.synthetic_probe.new_importer"]
    return {
        "protocols_to_models": current["protocols_to_models"],
        "hub_inbound": hub_inbound,
    }


def test_no_new_hard_fail_edges(current: EdgeSets, baseline: EdgeSets) -> None:
    """The live graph adds no hard-fail edge/importer outside the frozen baseline."""
    violations = find_violations(current, baseline)
    assert violations == {}, (
        "Import-layering growth ratchet violated — new hard-fail edge(s):\n"
        + "\n".join(f"  {k}: {v}" for k, v in violations.items())
    )


def test_no_new_utils_warnings_on_clean_tree(
    current: EdgeSets, baseline: EdgeSets
) -> None:
    """A clean tree also produces no utils WARN (baseline == current at freeze)."""
    assert find_warnings(current, baseline) == {}


def test_headline_protocols_models_number_frozen() -> None:
    """The 'no permanent exception' number is locked; lowering it is a visible edit."""
    assert FROZEN_PROTOCOLS_MODELS_MAX == 65


def test_hub_enforcement_tiers_are_disjoint_and_cover_all_hubs() -> None:
    assert set(HARD_FAIL_HUBS).isdisjoint(WARN_HUBS)
    assert set(HARD_FAIL_HUBS) | set(WARN_HUBS) == set(HUBS)
    assert WARN_HUBS == ("utils",)


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


@pytest.mark.parametrize("hub", HARD_FAIL_HUBS)
def test_hard_fail_hub_flags_new_importer(
    hub: str, current: EdgeSets, baseline: EdgeSets
) -> None:
    """Synthetic proof: a net-new importer into a HARD-FAIL hub is a violation."""
    injected = _inject_hub_importer(current, hub)
    assert f"hub:{hub}" in find_violations(injected, baseline)
    # And it is NOT downgraded to a warning.
    assert f"hub:{hub}" not in find_warnings(injected, baseline)


def test_models_to_nodes_service_wrapper_relocation_is_not_new_mixins_growth(
    current: EdgeSets, baseline: EdgeSets
) -> None:
    """OMN-14291 moved existing service wrappers; unrelated mixins growth still fails."""
    for new_importer, old_importer in HUB_IMPORTER_RELOCATIONS["mixins"].items():
        assert new_importer in current["hub_inbound"]["mixins"]
        assert old_importer in baseline["hub_inbound"]["mixins"]

    violations = find_violations(current, baseline)
    assert "hub:mixins" not in violations

    injected = _inject_hub_importer(current, "mixins")
    assert "hub:mixins" in find_violations(injected, baseline)


@pytest.mark.parametrize("hub", WARN_HUBS)
def test_warn_hub_warns_but_does_not_fail(
    hub: str, current: EdgeSets, baseline: EdgeSets
) -> None:
    """Synthetic proof: a net-new importer into a WARN hub (utils) warns, not fails."""
    injected = _inject_hub_importer(current, hub)
    # Non-blocking: not a hard violation ...
    assert f"hub:{hub}" not in find_violations(injected, baseline)
    # ... but still surfaced as a warning (visibility preserved).
    assert f"hub:{hub}" in find_warnings(injected, baseline)


def test_main_exit_zero_when_only_utils_grows(
    monkeypatch: pytest.MonkeyPatch, current: EdgeSets
) -> None:
    """End-to-end: a utils-only new importer keeps `main()` at exit 0 (warn)."""
    from scripts.ci import check_import_ratchet as mod

    injected = _inject_hub_importer(current, "utils")
    monkeypatch.setattr(mod, "compute_current_edges", lambda: injected)
    assert mod.main([]) == 0
