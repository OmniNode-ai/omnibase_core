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
