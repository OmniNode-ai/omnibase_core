# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-19050 AC6 — only a runner-produced PASS may clear a prior FAIL.

Repairing the FAIL latch (attempt-scoped records, total order, the
independent-observation guard) opened a second door: any PASS record filed
after a FAIL, by anyone, at a different head would clear it. The ticket's own
measured escape — "hand-author a receipt" — would then work, which is exactly
what ``validator_occ_merge_eligibility`` tells operators not to do.

So a PASS supersedes a prior FAIL only when the receipt runner produced it:
both the record's ``superseder`` and the replacement's ``runner`` must name a
runner identity (``EnumReceiptRunnerIdentity``). A hand-authored PASS over a
FAIL is refused and the FAIL stands, with the reason in ``guard_note``.

What this does NOT change, each pinned below as a control:

* A runner-produced PASS at new code still clears the FAIL (AC1 path).
* A hand-authored PASS with no FAIL anywhere in its chain still resolves as it
  did before — the OMN-13888 correction flow for placeholder receipts.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_runner_identity import (
    EnumReceiptRunnerIdentity,
    is_receipt_runner_identity,
)
from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.validation.validator_occ_merge_eligibility import (
    EnumOccEligibilityReason,
    ModelOccEligibilityInput,
    validate_occ_merge_eligibility,
)
from omnibase_core.validation.validator_receipt_gate import (
    compute_contract_entry_sha256,
)
from omnibase_core.validation.validator_receipt_supersession import (
    resolve_supersession,
)

TICKET = "OMN-18868"
ITEM = "dod-occ-diff-derived-behavior-proof-pr-2751"
CHECK = "test_passes"
PR = 2751
COMMAND = "uv run pytest tests/unit/test_wire_compatibility.py"

RUNNER = "omnimarket-ci occ-receipt-runner"
HAND = "claude:sonnet:lane-hand-correction"
VERIFIER = "github-actions product-repo test execution"

FAIL_SHA = "bab99887" + "0" * 32
PASS_SHA = "668a565b" + "1" * 32


def _contract() -> dict[str, object]:
    return {
        "ticket_id": TICKET,
        "title": "diff-derived behavior proof",
        "dod_evidence": [
            {
                "id": ITEM,
                "description": "diff-derived behavior proof",
                "checks": [{"check_type": CHECK, "check_value": COMMAND}],
            }
        ],
    }


ENTRY = compute_contract_entry_sha256(_contract(), ITEM)


def _receipt(
    *, status: EnumReceiptStatus, commit_sha: str, runner: str = RUNNER
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": ITEM,
        "check_type": CHECK,
        "check_value": COMMAND,
        "status": status.value,
        "run_timestamp": datetime(2026, 9, 21, 16, 0, tzinfo=UTC),
        "commit_sha": commit_sha,
        "runner": runner,
        "verifier": VERIFIER,
        "probe_command": COMMAND,
        "probe_stdout": (
            "31 passed in 13.14s\n"
            if status is EnumReceiptStatus.PASS
            else "ERROR: no tags found in a depth-1 checkout\n"
        ),
        "exit_code": 0 if status is EnumReceiptStatus.PASS else 1,
        "pr_number": PR,
        "contract_entry_sha256": ENTRY,
    }


def _record(
    *, replacement: dict[str, object], minute: int, superseder: str = RUNNER
) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": ITEM,
        "check_type": CHECK,
        "supersedes": f"drift/dod_receipts/{TICKET}/{ITEM}/{CHECK}.yaml",
        "reason": "the declared check was executed for real in the product checkout",
        "superseder": superseder,
        "created_at": datetime(2026, 9, 21, 17, minute, tzinfo=UTC),
        "tombstone": False,
        "replacement": replacement,
    }


def _write_chain(root: Path, *records: dict[str, object]) -> Path:
    key_dir = root / "receipts" / TICKET / ITEM
    key_dir.mkdir(parents=True)
    base = _receipt(status=EnumReceiptStatus.PENDING, commit_sha=FAIL_SHA)
    base["probe_stdout"] = ""
    base["exit_code"] = None
    (key_dir / f"{CHECK}.yaml").write_text(
        yaml.safe_dump(base, sort_keys=True), encoding="utf-8"
    )
    for index, record in enumerate(records, start=1):
        (key_dir / f"{CHECK}.supersede.{PR}.{index:04d}.yaml").write_text(
            yaml.safe_dump(record, sort_keys=True), encoding="utf-8"
        )
    return root / "receipts"


def _runner_fail() -> dict[str, object]:
    return _record(
        replacement=_receipt(status=EnumReceiptStatus.FAIL, commit_sha=FAIL_SHA),
        minute=5,
    )


def _pass(*, superseder: str, runner: str) -> dict[str, object]:
    return _record(
        replacement=_receipt(
            status=EnumReceiptStatus.PASS, commit_sha=PASS_SHA, runner=runner
        ),
        minute=30,
        superseder=superseder,
    )


def _snapshot(root: Path, receipts: Path) -> ModelOccEligibilityInput:
    (root / "contracts").mkdir()
    (root / "contracts" / f"{TICKET}.yaml").write_text(
        yaml.safe_dump(_contract(), sort_keys=True), encoding="utf-8"
    )
    return ModelOccEligibilityInput(
        repo="omnimarket",
        pr_number=PR,
        pr_title=f"fix({TICKET}): diff-derived behavior proof",
        pr_body=f"Closes: {TICKET}",
        pr_branch="jonah/omn-18868-behavior-proof",
        pr_commit_shas=(FAIL_SHA, PASS_SHA),
        pr_commit_texts=(f"fix({TICKET}): behavior proof",),
        occ_commit_sha="c" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=receipts,
    )


# --------------------------------------------------------------------------- #
# Refusals
# --------------------------------------------------------------------------- #

HAND_AUTHORED = [
    pytest.param(HAND, HAND, id="superseder-and-runner-hand"),
    pytest.param(HAND, RUNNER, id="hand-superseder-claims-runner"),
    pytest.param(RUNNER, HAND, id="runner-superseder-hand-receipt"),
]


@pytest.mark.unit
@pytest.mark.parametrize(("superseder", "runner"), HAND_AUTHORED)
@pytest.mark.parametrize("with_pr", [True, False], ids=["tier1", "legacy"])
def test_hand_authored_pass_does_not_clear_a_runner_fail(
    tmp_path: Path, superseder: str, runner: str, with_pr: bool
) -> None:
    receipts = _write_chain(
        tmp_path, _runner_fail(), _pass(superseder=superseder, runner=runner)
    )

    resolution = resolve_supersession(
        receipts, TICKET, ITEM, CHECK, current_pr_number=PR if with_pr else None
    )

    assert resolution is not None
    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.FAIL
    assert resolution.receipt.commit_sha == FAIL_SHA
    assert resolution.guard_note is not None
    assert "no runner produced it" in resolution.guard_note


@pytest.mark.unit
def test_eligibility_refuses_a_hand_authored_pass_over_a_fail(
    tmp_path: Path,
) -> None:
    """AC6 falsifier: a hand-authored PASS must not make the PR eligible."""
    receipts = _write_chain(
        tmp_path, _runner_fail(), _pass(superseder=HAND, runner=HAND)
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path, receipts))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.NONPASS_RECEIPT
    assert result.missing_or_nonpass_receipts == (f"{TICKET}:{ITEM}:{CHECK}",)
    assert "no runner produced it" in result.detail


# --------------------------------------------------------------------------- #
# Controls: what must keep working
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_eligibility_accepts_a_runner_pass_over_a_fail(tmp_path: Path) -> None:
    """Positive control for the refusal above: same chain, runner-produced."""
    receipts = _write_chain(
        tmp_path, _runner_fail(), _pass(superseder=RUNNER, runner=RUNNER)
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path, receipts))

    assert result.eligible is True, result.detail
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE


@pytest.mark.unit
def test_hand_authored_pass_with_no_prior_fail_resolves_as_before(
    tmp_path: Path,
) -> None:
    """The OMN-13888 correction flow over a placeholder is not narrowed."""
    receipts = _write_chain(tmp_path, _pass(superseder=HAND, runner=HAND))

    resolution = resolve_supersession(
        receipts, TICKET, ITEM, CHECK, current_pr_number=PR
    )

    assert resolution is not None
    assert resolution.receipt is not None
    assert resolution.receipt.status is EnumReceiptStatus.PASS
    assert resolution.guard_note is None


@pytest.mark.unit
def test_runner_identity_matches_the_runner_spelling() -> None:
    """The fixtures above use the identity the runner actually writes."""
    assert RUNNER == EnumReceiptRunnerIdentity.OMNIMARKET_CI_OCC_RECEIPT_RUNNER
    assert is_receipt_runner_identity(RUNNER)
    assert not is_receipt_runner_identity(HAND)
    assert not is_receipt_runner_identity(None)
