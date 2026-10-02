# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for omnibase_core.handlers.handler_done_write_receipt_gate (OMN-20368).

The rule under test: a Done write needs a PASS dod_verify verdict whose checks
bind every acceptance criterion through ``binds_ac``. A merged PR is never
enough on its own.
"""

from __future__ import annotations

from typing import Any

import pytest

from omnibase_core.handlers.handler_done_write_receipt_gate import (
    ac_binding_gap,
    evaluate_done_write_receipt,
    extract_dod_verify_verdict,
    verdict_is_all_verified,
)

pytestmark = pytest.mark.unit

_DESCRIPTION = (
    "## Acceptance Criteria\n"
    "- **AC1**: the handler refuses a Done write without a receipt\n"
    "- **AC2**: the handler allows a Done write with a bound receipt\n"
)


def _check(evidence_id: str, status: str, binds_ac: list[str]) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "status": status,
        "proof_class": "behavior",
        "binds_ac": binds_ac,
    }


def _verdict(checks: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    verified = sum(1 for c in checks if c["status"] == "verified")
    verdict: dict[str, Any] = {
        "status": "verified",
        "total_checks": len(checks),
        "verified_count": verified,
        "failed_count": sum(1 for c in checks if c["status"] == "failed"),
        "non_probative_count": 0,
        "checks": checks,
    }
    verdict.update(overrides)
    return verdict


def test_bound_pass_receipt_allows() -> None:
    verdict = _verdict(
        [_check("t1", "verified", ["AC1"]), _check("t2", "verified", ["AC2"])]
    )
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-1", description=_DESCRIPTION, verdict=verdict
    )
    assert decision.allowed
    assert decision.reason == ""
    assert all(row.bound for row in decision.rows)


def test_no_verdict_refuses() -> None:
    """A merged PR with no receipt is a ``None`` verdict: refuse."""
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-1", description=_DESCRIPTION, verdict=None
    )
    assert not decision.allowed
    assert "no dod_verify verdict" in decision.reason


def test_green_receipt_that_binds_one_criterion_refuses_and_names_the_other() -> None:
    verdict = _verdict(
        [_check("t1", "verified", ["AC1"]), _check("t2", "verified", [])]
    )
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-1", description=_DESCRIPTION, verdict=verdict
    )
    assert not decision.allowed
    assert len(decision.unbound) == 1
    assert "AC2" in decision.reason


def test_receipt_with_no_binds_ac_at_all_refuses() -> None:
    verdict = _verdict(
        [{"evidence_id": "t1", "status": "verified", "proof_class": "behavior"}]
    )
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-1", description=_DESCRIPTION, verdict=verdict
    )
    assert not decision.allowed
    assert "no `binds_ac` on any check" in decision.reason


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "failed"},
        {"status": "skipped"},
        {"failed_count": 1},
        {"verified_count": 0},
        {"total_checks": 3},
    ],
)
def test_non_pass_verdict_refuses(overrides: dict[str, Any]) -> None:
    verdict = _verdict(
        [_check("t1", "verified", ["AC1"]), _check("t2", "verified", ["AC2"])],
        **overrides,
    )
    assert not verdict_is_all_verified(verdict)
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-1", description=_DESCRIPTION, verdict=verdict
    )
    assert not decision.allowed
    assert "is not a PASS" in decision.reason


def test_non_probative_check_does_not_discharge_a_criterion() -> None:
    verdict = _verdict(
        [_check("t1", "verified", ["AC1"]), _check("t2", "non_probative", ["AC2"])],
        non_probative_count=1,
    )
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-1", description=_DESCRIPTION, verdict=verdict
    )
    assert not decision.allowed
    assert "AC2" in decision.reason


def test_description_with_no_parseable_criteria_holds() -> None:
    verdict = _verdict([_check("t1", "verified", ["AC1"])])
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-1", description="Just prose, no criteria.", verdict=verdict
    )
    assert not decision.allowed


def test_stale_pin_does_not_discharge_a_criterion() -> None:
    check = _check("t1", "verified", ["AC1", "AC2"])
    check["ac_binding_hashes"] = {"AC1": "0" * 64, "AC2": "0" * 64}
    reason, unbound, _ = ac_binding_gap(_DESCRIPTION, _verdict([check]), "OMN-1")
    assert reason
    assert len(unbound) == 2


_STATE_MODEL = (
    "omnimarket.nodes.node_dod_verify.models.model_dod_verify_state.ModelDodVerifyState"
)
_SUMMARY_MODEL = (
    "omnibase_infra.cli.model_receipt_runtime_summary.ModelReceiptRuntimeSummary"
)


def test_extract_verdict_reads_both_declared_arms() -> None:
    verdict = _verdict([_check("t1", "verified", ["AC1"])])
    flat, why = extract_dod_verify_verdict(
        {"result_model": _STATE_MODEL, "result": verdict}
    )
    assert flat == verdict and why == ""
    nested, why = extract_dod_verify_verdict(
        {"result_model": _SUMMARY_MODEL, "result": {"terminal_payload": verdict}}
    )
    assert nested == verdict and why == ""


@pytest.mark.parametrize(
    "receipt",
    [
        {},
        {"result_model": "something.else", "result": {"total_checks": 1}},
        {"result_model": _STATE_MODEL, "result": {"status": "verified"}},
        {"result_model": _SUMMARY_MODEL, "result": {}},
    ],
)
def test_extract_verdict_refuses_an_undeclared_or_verdictless_receipt(
    receipt: dict[str, object],
) -> None:
    verdict, why = extract_dod_verify_verdict(receipt)
    assert verdict is None
    assert why
