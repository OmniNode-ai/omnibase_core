# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The receipt gate on the recorded dod_verify receipts of OMN-17690, OMN-18892 and OMN-18960 (OMN-26231).

Fixtures: ``tests/fixtures/omn26231/`` holds ``onex skill dod_verify <id>
--execution-audience hosted`` output exactly as the Done-write guard runs it,
recorded 2026-11-20 on a lab host and scrubbed of user and host names.

* ``OMN-17690.success-arm...`` and ``OMN-18960.success-arm...``: every check
  verified (11 of 11, 8 of 8); ``result_model`` names the model at
  ``omnimarket.models.model_dod_verify_state.ModelDodVerifyState``, where
  omnimarket moved it. The gate hard-coded the old
  ``omnimarket.nodes.node_dod_verify.models...`` path and refused it.
* ``OMN-18892.success-arm...``: 9 of 9, recorded with
  ``DOD_VERIFY_CHECK_TIMEOUT_S=180`` (one check takes 31.5 s against the
  verifier's default 30 s ceiling).
* ``OMN-18892.skipped-check.summary-arm...``: the same ticket at the default
  ceiling: 8 verified, 1 skipped (``check_budget_exceeded``). A check the
  verifier could not read is still a refusal (OMN-20368).
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from omnibase_core.nodes.node_done_write_receipt_gate_compute.handler_done_write_receipt_gate import (
    as_int,
    evaluate_done_write_receipt,
    extract_dod_verify_verdict,
    verdict_is_all_verified,
)

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "omn26231"

# (fixture file, ticket, total_checks, verified_count)
VERIFIED_RECEIPTS = [
    ("OMN-17690.success-arm.skill-result.json", "OMN-17690", 11, 11),
    ("OMN-18892.success-arm.skill-result.json", "OMN-18892", 9, 9),
    ("OMN-18960.success-arm.skill-result.json", "OMN-18960", 8, 8),
]
MOVED_MODEL = "omnimarket.models.model_dod_verify_state.ModelDodVerifyState"


def load(name: str) -> dict[str, Any]:
    loaded = json.loads((FIXTURES / name).read_text())
    assert isinstance(loaded, dict)
    return loaded


def checks_of(verdict: Mapping[str, object]) -> list[dict[str, Any]]:
    checks = verdict["checks"]
    assert isinstance(checks, list)
    return checks


def description_binding(verdict: Mapping[str, object]) -> str:
    """One behaviour-shaped criterion per label the verified checks bind."""
    labels = sorted(
        {
            str(label)
            for check in checks_of(verdict)
            if check["status"] == "verified"
            for label in check.get("binds_ac") or []
        },
        key=lambda label: int(label[2:]),
    )
    assert labels, "fixture binds no criterion"
    return "".join(
        f"* {label}: The behaviour named by {label} holds.\n" for label in labels
    )


@pytest.mark.parametrize(("name", "ticket", "total", "verified"), VERIFIED_RECEIPTS)
def test_recorded_receipt_is_read_and_its_counts_agree(
    name: str, ticket: str, total: int, verified: int
) -> None:
    receipt = load(name)
    assert receipt["result_model"] == MOVED_MODEL
    verdict, why = extract_dod_verify_verdict(receipt)
    assert why == ""
    assert verdict is not None
    assert verdict["ticket_id"] == ticket
    assert verdict["total_checks"] == total
    assert verdict["verified_count"] == verified
    assert verdict["failed_count"] == 0
    assert verdict["non_probative_count"] == 0
    assert verdict_is_all_verified(verdict)


@pytest.mark.parametrize(("name", "ticket", "_total", "_verified"), VERIFIED_RECEIPTS)
def test_recorded_receipt_is_accepted_by_the_gate(
    name: str, ticket: str, _total: int, _verified: int
) -> None:
    verdict, _ = extract_dod_verify_verdict(load(name))
    assert verdict is not None
    decision = evaluate_done_write_receipt(
        ticket_id=ticket, description=description_binding(verdict), verdict=verdict
    )
    assert decision.allowed, decision.reason


@pytest.mark.parametrize(
    "moved_to",
    [
        "omnimarket.models.model_dod_verify_state.ModelDodVerifyState",
        "omnimarket.nodes.node_dod_verify.models.model_dod_verify_state.ModelDodVerifyState",
        "omnimarket.somewhere.new.ModelDodVerifyState",
    ],
)
def test_a_moved_model_needs_no_gate_edit(moved_to: str) -> None:
    receipt = load("OMN-17690.success-arm.skill-result.json")
    receipt["result_model"] = moved_to
    verdict, why = extract_dod_verify_verdict(receipt)
    assert why == ""
    assert verdict is not None


@pytest.mark.parametrize(
    "result_model",
    [
        "ModelDodVerifyState",
        ".ModelDodVerifyState",
        "omnimarket.models.model_dod_verify_state.ModelSomethingElse",
        "omnimarket.models.model_dod_verify_state.ModelDodVerifyStateV2",
        "",
    ],
)
def test_an_undeclared_type_is_still_refused(result_model: str) -> None:
    receipt = load("OMN-17690.success-arm.skill-result.json")
    receipt["result_model"] = result_model
    verdict, why = extract_dod_verify_verdict(receipt)
    assert verdict is None
    assert why


def test_a_skipped_check_is_still_refused_with_its_counts() -> None:
    receipt = load("OMN-18892.skipped-check.summary-arm.skill-result.json")
    verdict, why = extract_dod_verify_verdict(receipt)
    assert why == ""
    assert verdict is not None
    assert (verdict["total_checks"], verdict["verified_count"]) == (9, 8)
    assert verdict["skipped_count"] == 1
    assert not verdict_is_all_verified(verdict)
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-18892",
        description=description_binding(verdict),
        verdict=verdict,
    )
    assert not decision.allowed
    assert "is not a PASS: status='skipped', total_checks=9, verified_count=8" in (
        decision.reason
    )


@pytest.mark.parametrize(("name", "ticket", "_total", "_verified"), VERIFIED_RECEIPTS)
def test_a_receipt_with_a_failed_check_is_still_refused(
    name: str, ticket: str, _total: int, _verified: int
) -> None:
    receipt = copy.deepcopy(load(name))
    verdict, _ = extract_dod_verify_verdict(receipt)
    assert verdict is not None
    description = description_binding(verdict)
    checks_of(verdict)[0]["status"] = "failed"
    verdict["verified_count"] = as_int(verdict["verified_count"]) - 1
    verdict["failed_count"] = 1
    verdict["status"] = "failed"
    decision = evaluate_done_write_receipt(
        ticket_id=ticket, description=description, verdict=verdict
    )
    assert not decision.allowed
    assert "failed_count=1" in decision.reason


def test_an_absent_or_unreadable_receipt_is_still_refused() -> None:
    decision = evaluate_done_write_receipt(
        ticket_id="OMN-17690", description="* AC1: x.\n", verdict=None
    )
    assert not decision.allowed
    verdict, why = extract_dod_verify_verdict({"result": {"total_checks": 1}})
    assert verdict is None
    assert why
