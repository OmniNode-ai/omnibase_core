# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.validation.validator_occ_merge_eligibility import (
    EnumOccEligibilityReason,
    ModelOccEligibilityInput,
    validate_occ_merge_eligibility,
)

TICKET = "OMN-10484"
PR_SHA = "1" * 40
STALE_HASH = f"sha256:{'0' * 64}"


def _contract_text(ticket_id: str = TICKET) -> str:
    return yaml.safe_dump(
        {
            "ticket_id": ticket_id,
            "title": "OCC eligibility",
            "dod_evidence": [
                {
                    "id": "dod-001",
                    "description": "focused tests pass",
                    "checks": [
                        {
                            "check_type": "command",
                            "check_value": "uv run pytest tests/unit/validation/test_occ_merge_eligibility.py -q",
                        }
                    ],
                }
            ],
        },
        sort_keys=True,
    )


def _contract_hash(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def _write_contract(root: Path, ticket_id: str = TICKET) -> str:
    text = _contract_text(ticket_id)
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    (root / "contracts" / f"{ticket_id}.yaml").write_text(text, encoding="utf-8")
    return _contract_hash(text)


def _write_receipt(
    root: Path,
    *,
    ticket_id: str = TICKET,
    evidence_item_id: str = "dod-001",
    status: EnumReceiptStatus = EnumReceiptStatus.PASS,
    pr_number: int | None = 123,
    commit_sha: str = PR_SHA,
    contract_sha256: str | None,
) -> None:
    receipt = {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": evidence_item_id,
        "check_type": "command",
        "check_value": "uv run pytest tests/unit/validation/test_occ_merge_eligibility.py -q",
        "status": status.value,
        "run_timestamp": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "commit_sha": commit_sha,
        "runner": "worker",
        "verifier": "foreground",
        "probe_command": "uv run pytest tests/unit/validation/test_occ_merge_eligibility.py -q",
        "probe_stdout": "1 passed\n",
        "exit_code": 0,
        "pr_number": pr_number,
    }
    if contract_sha256 is not None:
        receipt["contract_sha256"] = contract_sha256
    path = root / "receipts" / ticket_id / evidence_item_id / "command.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(receipt, sort_keys=True),
        encoding="utf-8",
    )


def _write_multi_entry_contract(
    root: Path,
    evidence_item_ids: tuple[str, ...],
    *,
    ticket_id: str = TICKET,
) -> str:
    """Write a contract carrying one dod_evidence entry per id, return its hash."""
    text = yaml.safe_dump(
        {
            "ticket_id": ticket_id,
            "title": "multi-entry OCC eligibility",
            "dod_evidence": [
                {
                    "id": item_id,
                    "description": f"probe {item_id}",
                    "checks": [
                        {"check_type": "command", "check_value": f"probe {item_id}"}
                    ],
                }
                for item_id in evidence_item_ids
            ],
        },
        sort_keys=True,
    )
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    (root / "contracts" / f"{ticket_id}.yaml").write_text(text, encoding="utf-8")
    return _contract_hash(text)


def _snapshot(
    root: Path, *, body: str | None = None, title: str | None = None
) -> ModelOccEligibilityInput:
    return ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=123,
        pr_title=title or f"feat({TICKET}): harden OCC eligibility",
        pr_body=body or f"Closes: {TICKET}",
        pr_branch=f"jonah/{TICKET.lower()}-occ-eligibility",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=(f"feat({TICKET}): add eligibility",),
        occ_commit_sha="b" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=root / "receipts",
    )


@pytest.mark.unit
def test_missing_ticket_is_ineligible(tmp_path: Path) -> None:
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, body="No ticket here", title="docs: no ticket")
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_TICKET


@pytest.mark.unit
def test_ticket_not_bound_to_pr_is_ineligible(tmp_path: Path) -> None:
    contract_hash = _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=contract_hash)
    snapshot = ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=123,
        pr_title="feat: unrelated title",
        pr_body=f"Closes: {TICKET}",
        pr_branch="jonah/no-ticket-here",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=("feat: unrelated commit",),
        occ_commit_sha="b" * 40,
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.PR_TICKET_MISMATCH


@pytest.mark.unit
def test_ticket_binding_uses_full_ticket_tokens(tmp_path: Path) -> None:
    contract_hash = _write_contract(tmp_path, ticket_id="OMN-1")
    _write_receipt(tmp_path, ticket_id="OMN-1", contract_sha256=contract_hash)
    snapshot = ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=123,
        pr_title="feat(OMN-10484): harden OCC eligibility",
        pr_body="Closes: OMN-1",
        pr_branch="jonah/omn-10484-occ-eligibility",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=("feat(OMN-10484): add eligibility",),
        occ_commit_sha="b" * 40,
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.PR_TICKET_MISMATCH


@pytest.mark.unit
def test_missing_contract_is_ineligible(tmp_path: Path) -> None:
    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_CONTRACT
    assert result.missing_contracts == (TICKET,)


@pytest.mark.unit
def test_contract_directory_is_reported_as_missing_contract(tmp_path: Path) -> None:
    (tmp_path / "contracts" / f"{TICKET}.yaml").mkdir(parents=True)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_CONTRACT
    assert result.missing_contracts == (TICKET,)


@pytest.mark.unit
def test_missing_receipt_is_ineligible(tmp_path: Path) -> None:
    _write_contract(tmp_path)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT
    assert result.missing_or_nonpass_receipts == (f"{TICKET}:dod-001:command",)


@pytest.mark.unit
def test_nonpass_receipt_is_ineligible(tmp_path: Path) -> None:
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path, status=EnumReceiptStatus.FAIL, contract_sha256=contract_hash
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.NONPASS_RECEIPT


@pytest.mark.unit
def test_receipt_without_pr_or_commit_binding_is_ineligible(tmp_path: Path) -> None:
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.PR_TICKET_MISMATCH


@pytest.mark.unit
def test_receipt_bound_by_commit_sha_only_is_eligible(tmp_path: Path) -> None:
    """OMN-14456: commit_sha binding alone must be honored.

    Regression contract for the chicken-and-egg mint path: a receipt produced
    before the PR existed carries no pr_number, but its commit_sha matches one
    of the PR's current commits. `_receipt_bound_to_pr` must accept this even
    though pr_number is a foreign value — this is the *first-run* binding.
    Tightening the predicate to require both bindings would flip this red.
    """
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=999,  # foreign PR number: this binding must not matter here
        commit_sha=PR_SHA,  # matches snapshot.pr_commit_shas
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE


@pytest.mark.unit
def test_receipt_bound_by_pr_number_only_is_eligible(tmp_path: Path) -> None:
    """OMN-14456: pr_number binding alone must be honored.

    Regression contract for rebase survival: a rebase rewrites every commit
    SHA on the branch, so a receipt's original commit_sha binding is
    destroyed, but pr_number is untouched by a rebase. `_receipt_bound_to_pr`
    must accept a receipt whose pr_number matches the PR even though none of
    its commit_sha matches the PR's (rebased) commit set. Tightening the
    predicate to require both bindings would flip this red.
    """
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=123,  # matches snapshot.pr_number
        commit_sha="c" * 40,  # foreign SHA: simulates a post-rebase mismatch
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE


@pytest.mark.unit
def test_at_least_one_ticket_receipt_must_bind_to_pr(tmp_path: Path) -> None:
    contract = {
        "ticket_id": TICKET,
        "title": "multi PR ticket",
        "dod_evidence": [
            {
                "id": "dod-001",
                "checks": [{"check_type": "command", "check_value": "a"}],
            },
            {
                "id": "dod-002",
                "checks": [{"check_type": "command", "check_value": "b"}],
            },
        ],
    }
    contract_text = yaml.safe_dump(contract, sort_keys=True)
    (tmp_path / "contracts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "contracts" / f"{TICKET}.yaml").write_text(
        contract_text, encoding="utf-8"
    )
    contract_hash = _contract_hash(contract_text)
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-001",
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=contract_hash,
    )
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-002",
        pr_number=123,
        commit_sha=PR_SHA,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True
    assert result.receipt_ids == (
        f"{TICKET}:dod-001:command",
        f"{TICKET}:dod-002:command",
    )


@pytest.mark.unit
def test_contract_hash_mismatch_is_ineligible(tmp_path: Path) -> None:
    _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=f"sha256:{'0' * 64}")

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH


@pytest.mark.unit
def test_missing_contract_hash_is_ineligible_post_cutoff(tmp_path: Path) -> None:
    """contract_sha256=None must hard-fail (OMN-13061 / OMN-10421 post-cutoff).

    The migration window closed on 2026-04-30; receipts without a contract hash
    no longer pass silently — this aligns with validator_receipt_gate behaviour.
    """
    _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=None)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH
    assert "contract_sha256" in (result.detail or "")
    assert "OMN-10421" in (result.detail or "")


@pytest.mark.unit
def test_bare_contract_hash_is_migration_compatible(tmp_path: Path) -> None:
    contract_hash = _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=contract_hash.removeprefix("sha256:"))

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert result.contract_hashes == {TICKET: contract_hash}


@pytest.mark.unit
def test_eligible_output_is_replay_stable(tmp_path: Path) -> None:
    contract_hash = _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=contract_hash)
    snapshot = _snapshot(tmp_path)

    first = validate_occ_merge_eligibility(snapshot)
    second = validate_occ_merge_eligibility(snapshot)

    assert first.eligible is True
    assert first.reason is EnumOccEligibilityReason.ELIGIBLE
    assert first.to_json() == second.to_json()
    assert first.occ_commit_sha == "b" * 40
    assert first.contract_hashes == {TICKET: contract_hash}
    assert first.receipt_ids == (f"{TICKET}:dod-001:command",)


# --- OMN-14404: batch-report every stale receipt binding -----------------------
#
# The validator used to return on the FIRST stale binding, discarding the other
# N-1 receipts it had already resolved. Operators therefore learned about exactly
# one stale receipt per CI round: repair it, re-run, get the next. That is what
# manufactured the #3965 -> #3966 -> #3968 -> #3969 serial OCC repair chain on
# 2026-07-11 (#3965 fixed one receipt; #3966 fixed "the remaining").


@pytest.mark.unit
def test_all_stale_receipt_bindings_are_reported_not_just_the_first(
    tmp_path: Path,
) -> None:
    """N>1 stale bindings must ALL be named in a single result.

    This is the regression that proves the first-fail-only bug is dead: against
    the pre-fix validator it sees only dod-001.
    """
    item_ids = ("dod-001", "dod-002", "dod-003")
    _write_multi_entry_contract(tmp_path, item_ids)
    for item_id in item_ids:
        _write_receipt(tmp_path, evidence_item_id=item_id, contract_sha256=STALE_HASH)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH
    assert result.stale_receipt_bindings == tuple(
        f"{TICKET}:{item_id}:command" for item_id in item_ids
    )
    # the operator-facing detail names every stale receipt, not only the first
    for item_id in item_ids:
        assert item_id in result.detail
    assert "3 receipts have stale contract bindings" in result.detail


@pytest.mark.unit
def test_stale_receipt_bindings_batch_across_multiple_tickets(tmp_path: Path) -> None:
    """Accumulation spans tickets: the loop no longer aborts on the first one."""
    second_ticket = "OMN-10485"
    _write_contract(tmp_path)
    _write_contract(tmp_path, ticket_id=second_ticket)
    _write_receipt(tmp_path, contract_sha256=STALE_HASH)
    _write_receipt(tmp_path, ticket_id=second_ticket, contract_sha256=STALE_HASH)
    snapshot = ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=123,
        pr_title=f"feat({TICKET}): harden OCC eligibility",
        pr_body=f"Closes: {TICKET}\nCloses: {second_ticket}",
        pr_branch=f"jonah/{TICKET.lower()}-occ-eligibility",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=(
            f"feat({TICKET}): add eligibility",
            f"feat({second_ticket}): add eligibility",
        ),
        occ_commit_sha="b" * 40,
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH
    assert result.stale_receipt_bindings == (
        f"{TICKET}:dod-001:command",
        f"{second_ticket}:dod-001:command",
    )


@pytest.mark.unit
def test_single_stale_receipt_binding_reporting_is_unchanged(tmp_path: Path) -> None:
    """The N=1 case keeps its pre-batching reason and detail wording."""
    _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=STALE_HASH)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH
    assert result.stale_receipt_bindings == (f"{TICKET}:dod-001:command",)
    assert result.detail.startswith("receipt ")
    assert "receipts have stale contract bindings" not in result.detail


@pytest.mark.unit
def test_stale_bindings_take_precedence_over_missing_and_nonpass_receipts(
    tmp_path: Path,
) -> None:
    """Precedence is unchanged: a stale binding dominates missing/non-PASS.

    Pre-fix, the stale binding returned from inside the loop, so it preempted the
    post-loop MISSING_RECEIPT / NONPASS_RECEIPT report in every iteration order.
    Batch-reporting preserves that: the stale set is checked first.
    """
    contract_hash = _write_multi_entry_contract(
        tmp_path, ("dod-001", "dod-002", "dod-003")
    )
    _write_receipt(tmp_path, evidence_item_id="dod-001", contract_sha256=STALE_HASH)
    # dod-002 gets no receipt at all -> MISSING_RECEIPT class
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-003",
        status=EnumReceiptStatus.FAIL,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH
    assert result.stale_receipt_bindings == (f"{TICKET}:dod-001:command",)
    # the missing/non-PASS set is not surfaced while a stale binding outranks it,
    # matching the pre-fix early-return payload
    assert result.missing_or_nonpass_receipts == ()


@pytest.mark.unit
def test_zero_stale_bindings_stays_eligible_with_empty_stale_set(
    tmp_path: Path,
) -> None:
    contract_hash = _write_multi_entry_contract(tmp_path, ("dod-001", "dod-002"))
    _write_receipt(tmp_path, evidence_item_id="dod-001", contract_sha256=contract_hash)
    _write_receipt(tmp_path, evidence_item_id="dod-002", contract_sha256=contract_hash)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE
    assert result.stale_receipt_bindings == ()


@pytest.mark.unit
def test_batched_stale_binding_output_is_replay_stable(tmp_path: Path) -> None:
    item_ids = ("dod-001", "dod-002", "dod-003")
    _write_multi_entry_contract(tmp_path, item_ids)
    for item_id in item_ids:
        _write_receipt(tmp_path, evidence_item_id=item_id, contract_sha256=STALE_HASH)
    snapshot = _snapshot(tmp_path)

    first = validate_occ_merge_eligibility(snapshot)
    second = validate_occ_merge_eligibility(snapshot)

    assert first.to_json() == second.to_json()
    assert "stale_receipt_bindings" in first.to_json()


def _write_contract_dict(root: Path, contract: dict[str, object]) -> str:
    text = yaml.safe_dump(contract, sort_keys=True)
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    (root / "contracts" / f"{TICKET}.yaml").write_text(text, encoding="utf-8")
    return _contract_hash(text)


@pytest.mark.unit
def test_disclosed_skip_supersession_exempts_superseded_receipt(
    tmp_path: Path,
) -> None:
    """OMN-15664 AC5 / OMN-15413 AC6 regression.

    A superseded item's original checks stay in the contract (append-only)
    and would otherwise require an active receipt forever, even after a
    later item honestly declares the superseded item's evidence
    unprovable (``status: skipped``, no ``checks``) via
    ``evidence_artifact: supersedes_dod_evidence:<id>``. That superseded
    item's own receipt requirement must be excused -- there is no PASS
    receipt for it anywhere in this fixture, and eligibility must still be
    True because another, unrelated dod entry (dod-001) carries the
    PR-bound PASS receipt.
    """
    contract = {
        "ticket_id": TICKET,
        "title": "disclosed-skip supersession",
        "dod_evidence": [
            {
                "id": "dod-001",
                "checks": [{"check_type": "command", "check_value": "a"}],
            },
            {
                "id": "dod-002-always-true",
                "checks": [{"check_type": "command", "check_value": "b"}],
            },
            {
                "id": "dod-002-disclosed-skip",
                "checks": [],
                "status": "skipped",
                "evidence_artifact": "supersedes_dod_evidence:dod-002-always-true",
            },
        ],
    }
    contract_hash = _write_contract_dict(tmp_path, contract)
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-001",
        contract_sha256=contract_hash,
    )
    # No receipt at all for dod-002-always-true or dod-002-disclosed-skip.

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE


@pytest.mark.unit
def test_undisclosed_empty_checks_supersession_fails_closed(tmp_path: Path) -> None:
    """The exemption requires an EXPLICIT status: skipped declaration.

    A superseding item with empty checks and no "skipped" status (e.g. left
    at the schema default "pending") must NOT excuse the item it claims to
    supersede -- fail closed, the original receipt requirement stands. This
    is the guard against a bare placeholder entry silently laundering an
    unprovable requirement out of the gate.
    """
    contract = {
        "ticket_id": TICKET,
        "title": "undisclosed empty-checks supersession",
        "dod_evidence": [
            {
                "id": "dod-001",
                "checks": [{"check_type": "command", "check_value": "a"}],
            },
            {
                "id": "dod-002-always-true",
                "checks": [{"check_type": "command", "check_value": "b"}],
            },
            {
                "id": "dod-002-placeholder",
                "checks": [],
                "evidence_artifact": "supersedes_dod_evidence:dod-002-always-true",
            },
        ],
    }
    contract_hash = _write_contract_dict(tmp_path, contract)
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-001",
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT
    assert f"{TICKET}:dod-002-always-true:command" in result.missing_or_nonpass_receipts


@pytest.mark.unit
@pytest.mark.parametrize(
    ("checks_value", "include_checks"),
    [
        ([{}], True),
        (None, False),
        (None, True),
    ],
)
def test_malformed_disclosed_skip_supersession_fails_closed(
    tmp_path: Path,
    checks_value: object,
    include_checks: bool,
) -> None:
    """Skipped supersessions only excuse targets with checks exactly ``[]``.

    ``checks: [{}]`` is non-emittable, while omitted and null checks have no
    replacement receipt key. All three must leave the original receipt
    requirement intact.
    """
    superseding_item: dict[str, object] = {
        "id": "dod-002-malformed-skip",
        "status": "skipped",
        "evidence_artifact": "supersedes_dod_evidence:dod-002-always-true",
    }
    if include_checks:
        superseding_item["checks"] = checks_value
    contract = {
        "ticket_id": TICKET,
        "title": "malformed disclosed-skip supersession",
        "dod_evidence": [
            {
                "id": "dod-001",
                "checks": [{"check_type": "command", "check_value": "a"}],
            },
            {
                "id": "dod-002-always-true",
                "checks": [{"check_type": "command", "check_value": "b"}],
            },
            superseding_item,
        ],
    }
    contract_hash = _write_contract_dict(tmp_path, contract)
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-001",
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT
    assert f"{TICKET}:dod-002-always-true:command" in result.missing_or_nonpass_receipts


@pytest.mark.unit
def test_checked_replacement_supersession_still_requires_its_own_receipt(
    tmp_path: Path,
) -> None:
    """A supersession with real checks re-points the requirement, not removes it.

    dod-002-old is honestly superseded by dod-002-new (which carries its own
    checks), so dod-002-old's receipt is excused -- but dod-002-new is a
    normal dod entry and independently needs its own PASS receipt. With no
    receipt for dod-002-new at all, eligibility is ineligible on
    dod-002-new's key, never dod-002-old's.
    """
    contract = {
        "ticket_id": TICKET,
        "title": "checked replacement supersession",
        "dod_evidence": [
            {
                "id": "dod-001",
                "checks": [{"check_type": "command", "check_value": "a"}],
            },
            {
                "id": "dod-002-old",
                "checks": [{"check_type": "command", "check_value": "b-old"}],
            },
            {
                "id": "dod-002-new",
                "checks": [{"check_type": "command", "check_value": "b-new"}],
                "evidence_artifact": "supersedes_dod_evidence:dod-002-old",
            },
        ],
    }
    contract_hash = _write_contract_dict(tmp_path, contract)
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-001",
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT
    assert result.missing_or_nonpass_receipts == (f"{TICKET}:dod-002-new:command",)


# --- OMN-16353: missing-self-bind-only case emits an actionable reason ---------
#
# A hand-authored OCC companion that creates or extends a contract needs a
# receipt binding the ticket to the OCC PR ITSELF (`occ-self-bind-pr-<N>`).
# Omitting it used to surface as a generic `pr_ticket_mismatch` whose JSON
# reported every receipt as found and valid — actively misleading (three
# occurrences in one 2026-08-21 session: OCC#6819, #6820, #6675). When the
# ONLY defect is the missing self-bind (contracts resolve, receipts PASS,
# hashes valid, no receipt binds to THIS OCC-repo PR), the gate must emit
# `missing_occ_self_bind` plus the exact YAML entry and receipt path to write.
# The verdict itself is unchanged: ineligible before, ineligible after.


def _occ_snapshot(
    root: Path, *, repo: str = "onex_change_control"
) -> ModelOccEligibilityInput:
    """Snapshot for a PR on the OCC evidence repo itself."""
    return ModelOccEligibilityInput(
        repo=repo,
        pr_number=123,
        pr_title=f"docs({TICKET}): OCC evidence companion",
        pr_body=f"Closes: {TICKET}",
        pr_branch=f"jonah/{TICKET.lower()}-companion",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=(f"docs({TICKET}): add contract + receipts",),
        occ_commit_sha="b" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=root / "receipts",
    )


@pytest.mark.unit
def test_missing_self_bind_only_emits_actionable_reason_on_occ_repo(
    tmp_path: Path,
) -> None:
    """The missing-self-bind-only case gets its own reason + exact remedy.

    Everything verifies (contract resolves, receipt is PASS and hash-bound);
    the ONLY defect is that the receipt binds a foreign PR, not this OCC PR.
    Pre-fix this returned the generic terminal ``pr_ticket_mismatch``.
    """
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=999,  # the product PR, not this OCC PR
        commit_sha="c" * 40,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_occ_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_OCC_SELF_BIND
    # the receipt is still reported as resolved — nothing is "missing"
    assert result.receipt_ids == (f"{TICKET}:dod-001:command",)
    assert result.missing_or_nonpass_receipts == ()
    assert result.stale_receipt_bindings == ()
    # remediation payload: exact entry id, contract file, receipt path,
    # pr_number, and the OMN-13888 hash-recompute reminder
    assert "occ-self-bind-pr-123" in result.detail
    assert f"contracts/{TICKET}.yaml" in result.detail
    assert (
        f"drift/dod_receipts/{TICKET}/occ-self-bind-pr-123/command.yaml"
        in result.detail
    )
    assert "pr_number: 123" in result.detail
    assert "contract_sha256" in result.detail
    assert "contract_entry_sha256" in result.detail
    assert "OMN-13888" in result.detail


@pytest.mark.unit
def test_missing_self_bind_reason_accepts_org_qualified_occ_repo(
    tmp_path: Path,
) -> None:
    """A caller passing the org-qualified repo name gets the same reason."""
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(
        _occ_snapshot(tmp_path, repo="OmniNode-ai/onex_change_control")
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_OCC_SELF_BIND


@pytest.mark.unit
def test_missing_self_bind_reason_rejects_same_name_other_org_repo(
    tmp_path: Path,
) -> None:
    """A repo that merely shares the short name under a DIFFERENT org is not
    the canonical OCC repo — it must NOT get OCC self-bind remediation.

    CodeRabbit finding on OMN-16353's initial diff: matching on the bare
    suffix (``rsplit("/")[-1] == "onex_change_control"``) would misclassify
    ``other-org/onex_change_control`` as the OCC evidence repo. Only the bare
    short name or the exact canonical ``OmniNode-ai/onex_change_control`` may
    resolve to MISSING_OCC_SELF_BIND.
    """
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(
        _occ_snapshot(tmp_path, repo="other-org/onex_change_control")
    )

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.PR_TICKET_MISMATCH
    assert "occ-self-bind" not in result.detail


@pytest.mark.unit
def test_unbound_receipt_on_product_repo_keeps_pr_ticket_mismatch(
    tmp_path: Path,
) -> None:
    """Product-repo behavior is byte-identical: the self-bind remedy is an
    OCC-companion concept, so a product PR keeps the generic terminal reason."""
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=contract_hash,
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.PR_TICKET_MISMATCH
    assert "no PASS receipt for one or more tickets binds to PR #123" in result.detail
    assert "occ-self-bind" not in result.detail


@pytest.mark.unit
def test_missing_self_bind_does_not_absorb_missing_receipt(tmp_path: Path) -> None:
    """A genuinely missing receipt on the OCC repo stays MISSING_RECEIPT."""
    _write_contract(tmp_path)

    result = validate_occ_merge_eligibility(_occ_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT


@pytest.mark.unit
def test_missing_self_bind_does_not_absorb_nonpass_receipt(tmp_path: Path) -> None:
    """A FAIL receipt on the OCC repo stays NONPASS_RECEIPT."""
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path, status=EnumReceiptStatus.FAIL, contract_sha256=contract_hash
    )

    result = validate_occ_merge_eligibility(_occ_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.NONPASS_RECEIPT


@pytest.mark.unit
def test_missing_self_bind_does_not_absorb_stale_binding(tmp_path: Path) -> None:
    """A stale contract hash on the OCC repo stays CONTRACT_HASH_MISMATCH."""
    _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=STALE_HASH)

    result = validate_occ_merge_eligibility(_occ_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH


@pytest.mark.unit
def test_missing_self_bind_does_not_absorb_missing_contract(tmp_path: Path) -> None:
    """A missing contract on the OCC repo stays MISSING_CONTRACT."""
    result = validate_occ_merge_eligibility(_occ_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_CONTRACT


@pytest.mark.unit
def test_missing_self_bind_does_not_absorb_unbound_ticket_text(
    tmp_path: Path,
) -> None:
    """The EARLY pr_ticket_mismatch (ticket cited but not bound through PR
    title/branch/commit/Evidence-Ticket) is a different defect and keeps its
    reason even on the OCC repo."""
    contract_hash = _write_contract(tmp_path)
    _write_receipt(tmp_path, contract_sha256=contract_hash)
    snapshot = ModelOccEligibilityInput(
        repo="onex_change_control",
        pr_number=123,
        pr_title="docs: evidence companion without ticket token",
        pr_body=f"Closes: {TICKET}",
        pr_branch="jonah/no-ticket-here",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=("docs: unrelated commit",),
        occ_commit_sha="b" * 40,
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.PR_TICKET_MISMATCH
    assert "cited but not bound" in result.detail


@pytest.mark.unit
def test_missing_self_bind_names_every_unbound_ticket(tmp_path: Path) -> None:
    """With N unbound tickets, the remediation names each one (no serial
    one-per-CI-round drip)."""
    second_ticket = "OMN-10485"
    first_hash = _write_contract(tmp_path)
    second_hash = _write_contract(tmp_path, ticket_id=second_ticket)
    _write_receipt(
        tmp_path, pr_number=999, commit_sha="c" * 40, contract_sha256=first_hash
    )
    _write_receipt(
        tmp_path,
        ticket_id=second_ticket,
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=second_hash,
    )
    snapshot = ModelOccEligibilityInput(
        repo="onex_change_control",
        pr_number=123,
        pr_title=f"docs({TICKET}): companion",
        pr_body=f"Closes: {TICKET}\nCloses: {second_ticket}",
        pr_branch=f"jonah/{TICKET.lower()}-companion",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=(
            f"docs({TICKET}): contract",
            f"docs({second_ticket}): contract",
        ),
        occ_commit_sha="b" * 40,
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_OCC_SELF_BIND
    assert f"contracts/{TICKET}.yaml" in result.detail
    assert f"contracts/{second_ticket}.yaml" in result.detail
    assert f"drift/dod_receipts/{second_ticket}/occ-self-bind-pr-123" in result.detail


@pytest.mark.unit
def test_missing_self_bind_only_names_the_unbound_ticket(tmp_path: Path) -> None:
    """A ticket whose receipt DOES bind this PR is not named in the remedy."""
    second_ticket = "OMN-10485"
    first_hash = _write_contract(tmp_path)
    second_hash = _write_contract(tmp_path, ticket_id=second_ticket)
    # first ticket binds this PR; second binds only the foreign product PR
    _write_receipt(tmp_path, pr_number=123, contract_sha256=first_hash)
    _write_receipt(
        tmp_path,
        ticket_id=second_ticket,
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=second_hash,
    )
    snapshot = ModelOccEligibilityInput(
        repo="onex_change_control",
        pr_number=123,
        pr_title=f"docs({TICKET}): companion",
        pr_body=f"Closes: {TICKET}\nCloses: {second_ticket}",
        pr_branch=f"jonah/{TICKET.lower()}-companion",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=(
            f"docs({TICKET}): contract",
            f"docs({second_ticket}): contract",
        ),
        occ_commit_sha="b" * 40,
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
    )

    result = validate_occ_merge_eligibility(snapshot)

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_OCC_SELF_BIND
    assert f"drift/dod_receipts/{second_ticket}/occ-self-bind-pr-123" in result.detail
    assert f"drift/dod_receipts/{TICKET}/" not in result.detail


@pytest.mark.unit
def test_occ_repo_with_self_bind_receipt_stays_eligible(tmp_path: Path) -> None:
    """A properly self-bound OCC companion is eligible — verdicts unchanged."""
    contract_hash = _write_contract(tmp_path)
    _write_receipt(tmp_path, pr_number=123, contract_sha256=contract_hash)

    result = validate_occ_merge_eligibility(_occ_snapshot(tmp_path))

    assert result.eligible is True
    assert result.reason is EnumOccEligibilityReason.ELIGIBLE


@pytest.mark.unit
def test_missing_self_bind_output_is_replay_stable(tmp_path: Path) -> None:
    contract_hash = _write_contract(tmp_path)
    _write_receipt(
        tmp_path,
        pr_number=999,
        commit_sha="c" * 40,
        contract_sha256=contract_hash,
    )
    snapshot = _occ_snapshot(tmp_path)

    first = validate_occ_merge_eligibility(snapshot)
    second = validate_occ_merge_eligibility(snapshot)

    assert first.to_json() == second.to_json()
    assert '"reason":"missing_occ_self_bind"' in first.to_json()
