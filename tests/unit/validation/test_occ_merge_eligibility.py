# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.validation.occ_merge_eligibility import (
    EnumOccEligibilityReason,
    ModelOccEligibilityInput,
    validate_occ_merge_eligibility,
)

TICKET = "OMN-10484"
PR_SHA = "a1b2c3d4e5f678901234567890abcdef12345678"


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
    contract_sha256: str,
) -> None:
    path = root / "receipts" / ticket_id / evidence_item_id / "command.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
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
                "contract_sha256": contract_sha256,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


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
def test_missing_contract_is_ineligible(tmp_path: Path) -> None:
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
