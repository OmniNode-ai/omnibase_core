# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-16859 AC3c — a PENDING receipt on a runner-covered check_type is legible.

Context, in one paragraph. The OCC companion producers run in the .201 dev-lane
effects runtime, which holds NO product-repo checkout, so they cannot execute a
declared ``test_passes`` check. Until OMN-16859 the born receipt papered over
that by minting ``status: PASS`` behind a ``gh pr view`` probe. The honest mint
is ``status: PENDING`` ("the probe was allocated but has not yet executed" --
:class:`EnumReceiptStatus` docstring), and a product-repo CI runner later
supersedes it with a real executed run.

This module pins the eligibility half of that arrangement. The verdict does NOT
change: a PENDING receipt is ineligible, exactly as it was. What changes is the
REASON. Four independent lanes on 2026-08-28 hit the same defect and each
re-diagnosed it from scratch, because the gate said ``missing_receipt`` --
which points at the wrong remedy (hand-author a receipt) instead of the right
one (wait for, or fix, the runner).

The three properties that make this a legibility change and not a carve-out are
each pinned by their own test:

* ``test_awaiting_runner_is_still_ineligible`` -- fail-closed. If the runner
  never reports, the PR stays blocked forever.
* ``test_a_genuine_missing_receipt_outranks_awaiting_runner`` and
  ``test_a_genuine_failing_receipt_outranks_awaiting_runner`` -- the softer
  reason is reported ONLY when it is the sole remaining blocker, so no real
  failure can be laundered into "just waiting".
* ``test_pending_receipt_on_a_non_runner_check_type_stays_nonpass`` -- the
  carve-out is scoped to the check types a runner actually covers, not to
  PENDING in general.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.validation.validator_occ_merge_eligibility import (
    EnumOccEligibilityReason,
    ModelOccEligibilityInput,
    validate_occ_merge_eligibility,
)

TICKET = "OMN-16859"
PR_SHA = "3" * 40
PR_NUMBER = 2210
BEHAVIOR_ITEM = "dod-occ-diff-derived-behavior-proof"
BEHAVIOR_CHECK = (
    "uv run pytest tests/unit/scripts/test_occ_receipt_runner_omn_16859.py -q"
)


def _contract_text(items: list[dict[str, Any]]) -> str:
    return yaml.safe_dump(
        {
            "ticket_id": TICKET,
            "title": "automatic OCC receipt generation",
            "dod_evidence": items,
        },
        sort_keys=True,
    )


def _item(item_id: str, check_type: str, check_value: str) -> dict[str, Any]:
    return {
        "id": item_id,
        "description": f"probe {item_id}",
        "checks": [{"check_type": check_type, "check_value": check_value}],
    }


def _write_contract(root: Path, items: list[dict[str, Any]]) -> str:
    text = _contract_text(items)
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    (root / "contracts" / f"{TICKET}.yaml").write_text(text, encoding="utf-8")
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def _write_ticket_contract(
    root: Path, ticket_id: str, items: list[dict[str, Any]]
) -> str:
    text = yaml.safe_dump(
        {
            "ticket_id": ticket_id,
            "title": f"{ticket_id} contract",
            "dod_evidence": items,
        },
        sort_keys=True,
    )
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    (root / "contracts" / f"{ticket_id}.yaml").write_text(text, encoding="utf-8")
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def _write_receipt(
    root: Path,
    *,
    ticket_id: str = TICKET,
    evidence_item_id: str,
    check_type: str,
    check_value: str,
    status: EnumReceiptStatus,
    contract_sha256: str,
    commit_sha: str = PR_SHA,
    pr_number: int = PR_NUMBER,
) -> Path:
    """Write a receipt at the path eligibility resolves: ``<item>/<check_type>.yaml``."""
    executed = status is not EnumReceiptStatus.PENDING
    receipt: dict[str, Any] = {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": evidence_item_id,
        "check_type": check_type,
        "check_value": check_value,
        "status": status.value,
        "run_timestamp": datetime(2026, 8, 29, 11, 0, tzinfo=UTC),
        "commit_sha": commit_sha,
        # Distinct identities: `verifier == runner` downgrades PASS to ADVISORY
        # (ModelDodReceipt rule 1) and would make the PASS control below fail
        # for a reason that has nothing to do with this ticket.
        "runner": "github-actions/occ-receipt-runner",
        "verifier": "occ-receipt-runner exit-status assertion",
        "probe_command": check_value,
        # An unexecuted probe has no stdout, and ModelDodReceipt rule 3
        # explicitly exempts PENDING from the non-empty-stdout requirement.
        # Writing a fake "1 passed" here would defeat the point of the fixture.
        "probe_stdout": "" if not executed else "1 passed in 0.12s\n",
        "exit_code": None if not executed else 0,
        "pr_number": pr_number,
        "contract_sha256": contract_sha256,
    }
    path = root / "receipts" / ticket_id / evidence_item_id / f"{check_type}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(receipt, sort_keys=True), encoding="utf-8")
    return path


def _snapshot(root: Path) -> ModelOccEligibilityInput:
    return ModelOccEligibilityInput(
        repo="omnimarket",
        pr_number=PR_NUMBER,
        pr_title=f"feat({TICKET}): product-repo OCC receipt runner",
        pr_body=f"Closes: {TICKET}",
        pr_branch=f"jonah/{TICKET.lower()}-occ-receipt-runner",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=(f"feat({TICKET}): runner",),
        occ_commit_sha="c" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=root / "receipts",
    )


def _snapshot_for_tickets(root: Path, *ticket_ids: str) -> ModelOccEligibilityInput:
    return ModelOccEligibilityInput(
        repo="omnimarket",
        pr_number=PR_NUMBER,
        pr_title=" ".join(f"feat({ticket_id}): runner" for ticket_id in ticket_ids),
        pr_body="\n".join(f"Closes: {ticket_id}" for ticket_id in ticket_ids),
        pr_branch="jonah/multi-ticket-occ-receipt-runner",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=tuple(f"feat({ticket_id}): runner" for ticket_id in ticket_ids),
        occ_commit_sha="c" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=root / "receipts",
    )


def _only_pending_behavior_proof(root: Path) -> None:
    """The exact live shape: one declared test_passes item, receipt PENDING."""
    contract_hash = _write_contract(
        root, [_item(BEHAVIOR_ITEM, "test_passes", BEHAVIOR_CHECK)]
    )
    _write_receipt(
        root,
        evidence_item_id=BEHAVIOR_ITEM,
        check_type="test_passes",
        check_value=BEHAVIOR_CHECK,
        status=EnumReceiptStatus.PENDING,
        contract_sha256=contract_hash,
    )


@pytest.mark.unit
def test_pending_runner_covered_receipt_reports_awaiting_runner(
    tmp_path: Path,
) -> None:
    """The reason names the real situation, not a missing file.

    RED before OMN-16859: the receipt exists and resolves, so the gate falls
    through to ``NONPASS_RECEIPT`` -- indistinguishable from a check that ran
    and FAILED, and pointing the operator at hand-authoring a receipt.
    """
    _only_pending_behavior_proof(tmp_path)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.reason is EnumOccEligibilityReason.AWAITING_RUNNER_RECEIPT


@pytest.mark.unit
def test_awaiting_runner_is_still_ineligible(tmp_path: Path) -> None:
    """Fail-closed. This is the property that keeps the change honest.

    A PENDING receipt asserts nothing was executed. If the product-repo runner
    never reports, this PR never merges. The new reason buys legibility, never
    permission.
    """
    _only_pending_behavior_proof(tmp_path)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False


@pytest.mark.unit
def test_awaiting_runner_still_surfaces_the_receipt_key(tmp_path: Path) -> None:
    """The machine-readable key list does not go blind on the new reason.

    ``missing_or_nonpass_receipts`` is what CI logs and downstream tooling read
    to name the offending key. Reporting a new reason with an empty key list
    would trade one diagnosis problem for another.
    """
    _only_pending_behavior_proof(tmp_path)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.missing_or_nonpass_receipts == (
        f"{TICKET}:{BEHAVIOR_ITEM}:test_passes",
    )


@pytest.mark.unit
def test_unbound_ticket_outranks_awaiting_runner(tmp_path: Path) -> None:
    """A bound pending receipt cannot hide another ticket with no PR-bound proof."""
    other_ticket = "OMN-16860"
    other_item = "dod-other-bound-proof"
    contract_hash = _write_contract(
        tmp_path, [_item(BEHAVIOR_ITEM, "test_passes", BEHAVIOR_CHECK)]
    )
    other_contract_hash = _write_ticket_contract(
        tmp_path, other_ticket, [_item(other_item, "test_passes", "uv run pytest -q")]
    )
    _write_receipt(
        tmp_path,
        evidence_item_id=BEHAVIOR_ITEM,
        check_type="test_passes",
        check_value=BEHAVIOR_CHECK,
        status=EnumReceiptStatus.PENDING,
        contract_sha256=contract_hash,
    )
    _write_receipt(
        tmp_path,
        ticket_id=other_ticket,
        evidence_item_id=other_item,
        check_type="test_passes",
        check_value="uv run pytest -q",
        status=EnumReceiptStatus.PASS,
        contract_sha256=other_contract_hash,
        commit_sha="4" * 40,
        pr_number=9999,
    )

    result = validate_occ_merge_eligibility(
        _snapshot_for_tickets(tmp_path, TICKET, other_ticket)
    )

    assert result.reason is EnumOccEligibilityReason.PR_TICKET_MISMATCH
    assert other_ticket in result.detail


@pytest.mark.unit
def test_awaiting_runner_has_legacy_nonpass_reason_value(tmp_path: Path) -> None:
    """Older exhaustive consumers can keep their NONPASS_RECEIPT branch.

    The emitted reason remains specific for new consumers, while compatibility
    callers that have not yet added a dedicated branch can fail closed exactly
    as they did before OMN-16859.
    """
    _only_pending_behavior_proof(tmp_path)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.reason is EnumOccEligibilityReason.AWAITING_RUNNER_RECEIPT
    assert (
        result.reason.legacy_external_value()
        == EnumOccEligibilityReason.NONPASS_RECEIPT.value
    )


@pytest.mark.unit
def test_awaiting_runner_detail_names_the_remedy(tmp_path: Path) -> None:
    """The detail must say what will clear it, since that is the whole point.

    Four lanes re-diagnosed this from scratch because the message pointed at
    the wrong remedy. The detail names the check type and says a product-repo
    runner supersedes it, so the next lane reads the answer instead of
    re-deriving it.
    """
    _only_pending_behavior_proof(tmp_path)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert "test_passes" in result.detail
    assert "PENDING" in result.detail
    assert "runner" in result.detail.lower()


@pytest.mark.unit
def test_pending_receipt_on_a_non_runner_check_type_stays_nonpass(
    tmp_path: Path,
) -> None:
    """The carve-out is scoped to check types a runner covers, not to PENDING.

    ``file_exists`` has no product-repo runner behind it, so a PENDING receipt
    there is an ordinary non-PASS receipt and must keep saying so. Widening
    this to every PENDING status would turn "someone left a placeholder" into
    "the system is working on it".
    """
    contract_hash = _write_contract(
        tmp_path, [_item("dod-artifact", "file_exists", "docs/plan.md")]
    )
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-artifact",
        check_type="file_exists",
        check_value="docs/plan.md",
        status=EnumReceiptStatus.PENDING,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.NONPASS_RECEIPT


@pytest.mark.unit
def test_a_genuine_missing_receipt_outranks_awaiting_runner(tmp_path: Path) -> None:
    """A real gap still reports as a real gap.

    One PENDING runner-covered item plus one item with no receipt at all. The
    missing receipt is the harder failure and must win, or a PR with genuinely
    absent evidence would read as merely waiting on CI.
    """
    contract_hash = _write_contract(
        tmp_path,
        [
            _item(BEHAVIOR_ITEM, "test_passes", BEHAVIOR_CHECK),
            _item("dod-unwritten", "command", "echo never-minted"),
        ],
    )
    _write_receipt(
        tmp_path,
        evidence_item_id=BEHAVIOR_ITEM,
        check_type="test_passes",
        check_value=BEHAVIOR_CHECK,
        status=EnumReceiptStatus.PENDING,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT
    assert result.missing_or_nonpass_receipts == (
        f"{TICKET}:{BEHAVIOR_ITEM}:test_passes",
        f"{TICKET}:dod-unwritten:command",
    )


@pytest.mark.unit
def test_a_genuine_failing_receipt_outranks_awaiting_runner(tmp_path: Path) -> None:
    """A check that RAN and FAILED still reports as a failure.

    This is the adversarial case for the whole change: if AWAITING could mask a
    FAIL, the new reason would be a bypass rather than a label.
    """
    contract_hash = _write_contract(
        tmp_path,
        [
            _item(BEHAVIOR_ITEM, "test_passes", BEHAVIOR_CHECK),
            _item("dod-ran-and-failed", "command", "exit 1"),
        ],
    )
    _write_receipt(
        tmp_path,
        evidence_item_id=BEHAVIOR_ITEM,
        check_type="test_passes",
        check_value=BEHAVIOR_CHECK,
        status=EnumReceiptStatus.PENDING,
        contract_sha256=contract_hash,
    )
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-ran-and-failed",
        check_type="command",
        check_value="exit 1",
        status=EnumReceiptStatus.FAIL,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.NONPASS_RECEIPT
    assert result.missing_or_nonpass_receipts == (
        f"{TICKET}:{BEHAVIOR_ITEM}:test_passes",
        f"{TICKET}:dod-ran-and-failed:command",
    )


@pytest.mark.unit
def test_the_runners_executed_pass_clears_the_gate(tmp_path: Path) -> None:
    """Positive control: this is the state the runner exists to produce.

    Same contract, same key -- the only difference is that the check actually
    ran. If this did not go green the arrangement would have no exit, and the
    PENDING tests above would be pinning a permanent block.
    """
    contract_hash = _write_contract(
        tmp_path, [_item(BEHAVIOR_ITEM, "test_passes", BEHAVIOR_CHECK)]
    )
    _write_receipt(
        tmp_path,
        evidence_item_id=BEHAVIOR_ITEM,
        check_type="test_passes",
        check_value=BEHAVIOR_CHECK,
        status=EnumReceiptStatus.PASS,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
