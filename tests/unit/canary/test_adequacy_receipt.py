# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for the coverage-guided adequacy receipt (OMN-14353 #41)."""

from __future__ import annotations

import coverage
import pytest

from omnibase_core.nodes.node_routing_authority_check_compute import (
    handler as handler_mod,
)
from omnibase_core.nodes.node_routing_authority_check_compute.handler import (
    ModelResidueEntry,
    ModelRoutingAuthorityCheckInput,
    ModelRoutingContractEntry,
    NodeRoutingAuthorityCheckCompute,
)
from scripts.ci.adequacy_receipt import (
    ModelAdequacyReceipt,
    ModelUncoveredWaiver,
    build_receipt,
    handler_module_sha256,
    input_hash,
    scrub,
    select_covering,
)

pytestmark = pytest.mark.unit

# coverage.py does not support a second concurrent measurement, so the
# coverage-driven tests are skipped when the suite itself runs under --cov.
_COVERAGE_ACTIVE = coverage.Coverage.current() is not None
_needs_coverage = pytest.mark.skipif(
    _COVERAGE_ACTIVE,
    reason="nested coverage measurement unsupported (suite under --cov)",
)

_GOOD_CONTRACT = (
    "name: n\nnode_type: compute\nmodel_routing:\n"
    '  provider: "google"\n  served_model_id: "g"\n'
    '  endpoint_ref: "gemini_pro"\n  routing_source: "b.yaml"\n'
)
_GOOD_BIFROST = (
    'backends:\n  - backend_id: "gemini_pro"\n    tier: "cloud"\n'
    '    endpoint_url_env: "U"\n    endpoint_url: null\n'
)
_CLI_BIFROST = (
    'backends:\n  - backend_id: "cli-x"\n    tier: "cli_agents"\n'
    '    endpoint_url: "cli://x"\n'
)


def _mk(**kw: object) -> ModelRoutingAuthorityCheckInput:
    base: dict[str, object] = {
        "demo_path_contracts": (ModelRoutingContractEntry(contract_rel="c.yaml"),),
        "contract_contents": {"c.yaml": _GOOD_CONTRACT},
        "bifrost_config_rel": "b.yaml",
        "bifrost_config_content": _GOOD_BIFROST,
        "demo_path_sources": ("s.py",),
        "source_contents": {"s.py": "def h(p):\n    return p\n"},
        "residue_entries": (),
        "residue_contents": {},
    }
    base.update(kw)
    return ModelRoutingAuthorityCheckInput(**base)  # type: ignore[arg-type]


def _pool() -> list[ModelRoutingAuthorityCheckInput]:
    return [
        _mk(),
        _mk(
            contract_contents={"c.yaml": "name: b\nnode_type: compute\n"},
            bifrost_config_content=_CLI_BIFROST,
            source_contents={"s.py": 'import os\nE = os.getenv("SERVICE_ENDPOINT")\n'},
        ),
        _mk(
            residue_entries=(
                ModelResidueEntry(
                    file_rel="l.py", baseline_count=2, debt_ticket="T", description="d"
                ),
            ),
            residue_contents={
                "l.py": 'import os\nA=os.getenv("SERVICE_ENDPOINT")\nB=os.getenv("PROVIDER_HOST")\n'
            },
        ),
        _mk(contract_contents={"c.yaml": "{{bad yaml"}),
        _mk(contract_contents={"c.yaml": ""}),
        _mk(
            bifrost_config_content='backends:\n  - backend_id: "other"\n    endpoint_url: "https://x"\n'
        ),
        _mk(source_contents={"s.py": 'X = "openai"\n'}),
    ]


# --- pure helpers (no coverage) ---


def test_scrub_redacts_sensitive_keys_deeply() -> None:
    payload = {
        "api_key": "s",
        "keep": 1,
        "nested": {"password": "p", "ok": 2},
        "list": [{"auth_token": "t"}, {"fine": 3}],
    }
    out = scrub(payload)
    assert out["api_key"] == "<scrubbed>"
    assert out["keep"] == 1
    assert out["nested"]["password"] == "<scrubbed>"
    assert out["nested"]["ok"] == 2
    assert out["list"][0]["auth_token"] == "<scrubbed>"
    assert out["list"][1]["fine"] == 3


def test_input_hash_is_order_independent() -> None:
    a = _mk()
    b = _mk()
    assert input_hash(a) == input_hash(b)
    assert input_hash(a).startswith("sha256:")


def test_handler_module_sha256_matches_file() -> None:
    import hashlib
    from pathlib import Path

    expected = (
        "sha256:" + hashlib.sha256(Path(handler_mod.__file__).read_bytes()).hexdigest()
    )
    assert handler_module_sha256(handler_mod.__file__) == expected


def test_receipt_requires_waiver_below_target() -> None:
    with pytest.raises(ValueError, match="requires an explicit uncovered_waiver"):
        ModelAdequacyReceipt(
            node_id="n",
            handler_module="m",
            handler_module_sha256="sha256:x",
            recorded_at="2026-07-11T00:00:00+00:00",
            candidate_count=1,
            selected_count=1,
            selected_input_hashes=["sha256:a"],
            branch_coverage_pct=50.0,
            coverage_target=80.0,
            meets_target=False,
            uncovered_waiver=None,
            volatile_mask=[],
        )


def test_receipt_rejects_waiver_when_target_met() -> None:
    with pytest.raises(ValueError, match="uncovered_waiver forbidden"):
        ModelAdequacyReceipt(
            node_id="n",
            handler_module="m",
            handler_module_sha256="sha256:x",
            recorded_at="2026-07-11T00:00:00+00:00",
            candidate_count=1,
            selected_count=1,
            selected_input_hashes=["sha256:a"],
            branch_coverage_pct=90.0,
            coverage_target=80.0,
            meets_target=True,
            uncovered_waiver=ModelUncoveredWaiver(reason="x", uncovered_branch_count=0),
            volatile_mask=[],
        )


# --- coverage-driven (skipped under --cov) ---


@_needs_coverage
def test_selection_drops_redundant_candidates() -> None:
    handler = NodeRoutingAuthorityCheckCompute()
    base = _mk()
    # base twice + one distinct: the duplicate adds no new arcs, so it is dropped.
    candidates = [base, base, _mk(contract_contents={"c.yaml": "{{bad"})]
    selected_idx, _ = select_covering(
        handler_call=handler.check,
        candidates=candidates,
        source_match="node_routing_authority_check_compute",
    )
    assert len(selected_idx) < len(candidates)


def _receipt(target: float) -> ModelAdequacyReceipt:
    handler = NodeRoutingAuthorityCheckCompute()
    return build_receipt(
        node_id="node_routing_authority_check_compute",
        handler_module_file=handler_mod.__file__,
        handler_call=handler.check,
        candidates=_pool(),
        source_match="node_routing_authority_check_compute",
        volatile_mask=[],
        coverage_target=target,
    )


@_needs_coverage
def test_build_receipt_below_target_is_fail_closed_with_waiver() -> None:
    # An unreachable target forces below-target — the receipt MUST carry a waiver
    # (a node below target can never be silently canonical). This is the
    # load-bearing safety property, asserted independently of the node's absolute
    # coverage (the fixture handler's magnitude is not the thing under test).
    receipt = _receipt(target=100.0)
    assert 0.0 <= receipt.branch_coverage_pct <= 100.0
    assert receipt.meets_target is False
    assert receipt.uncovered_waiver is not None
    assert receipt.uncovered_waiver.reason
    assert receipt.selected_count <= receipt.candidate_count
    assert len(receipt.selected_input_hashes) == receipt.selected_count
    assert receipt.handler_module_sha256.startswith("sha256:")


@_needs_coverage
def test_build_receipt_at_zero_target_meets_without_waiver() -> None:
    # target=0 is trivially met — and the fail-closed validator FORBIDS a waiver
    # when the target is met, so this exercises the other branch of the invariant.
    receipt = _receipt(target=0.0)
    assert receipt.meets_target is True
    assert receipt.uncovered_waiver is None
