# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-13888 — per-entry hashing, append-only, supersession, dual-accept.

These regression tests prove the OCC merge-eligibility redesign:

* Class 1 — appending a dod_evidence entry does not invalidate prior receipts.
* Class 2 — supersession/tombstone re-bind or invalidate a key without edits.
* Class 3 — Nth-consumer lockout is gone; forgery + grandfather + dual-accept.
* Determinism — the per-entry hash is invariant across a yamlfmt-style reflow.
* Append-only — edit/remove of an entry or receipt file is a violation.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.models.contracts.ticket.model_receipt_supersession import (
    ModelReceiptSupersession,
)
from omnibase_core.validation.validator_occ_append_only import evaluate_append_only
from omnibase_core.validation.validator_occ_merge_eligibility import (
    EnumOccEligibilityReason,
    ModelOccEligibilityInput,
    validate_occ_merge_eligibility,
)
from omnibase_core.validation.validator_receipt_gate import (
    compute_contract_entry_sha256,
    parse_pr_opened_at,
    validate_pr_receipts,
)
from omnibase_core.validation.validator_receipt_supersession import (
    resolve_supersession,
)

TICKET = "OMN-13888"


def _entry(item_id: str, value: str) -> dict:
    return {
        "id": item_id,
        "description": f"entry {item_id}",
        "checks": [{"check_type": "command", "check_value": value}],
    }


def _contract(item_ids: list[str]) -> dict:
    return {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "title": "per-entry hashing",
        "dod_evidence": [_entry(i, f"cmd-{i}") for i in item_ids],
    }


def _write_contract(root: Path, contract: dict) -> Path:
    (root / "contracts").mkdir(parents=True, exist_ok=True)
    path = root / "contracts" / f"{TICKET}.yaml"
    path.write_text(yaml.safe_dump(contract, sort_keys=True), encoding="utf-8")
    return path


def _whole_file_hash(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _receipt_dict(
    *,
    item_id: str,
    pr_number: int,
    commit_sha: str,
    contract_entry_sha256: str | None = None,
    contract_sha256: str | None = None,
    status: EnumReceiptStatus = EnumReceiptStatus.PASS,
) -> dict:
    data = {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": item_id,
        "check_type": "command",
        "check_value": f"cmd-{item_id}",
        "status": status.value,
        "run_timestamp": datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        "commit_sha": commit_sha,
        "runner": "worker",
        "verifier": "independent-ci",
        "probe_command": f"run cmd-{item_id}",
        "probe_stdout": "1 passed\n",
        "exit_code": 0,
        "pr_number": pr_number,
    }
    if contract_entry_sha256 is not None:
        data["contract_entry_sha256"] = contract_entry_sha256
    if contract_sha256 is not None:
        data["contract_sha256"] = contract_sha256
    return data


def _write_receipt(root: Path, item_id: str, data: dict) -> Path:
    path = root / "receipts" / TICKET / item_id / "command.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
    return path


def _snapshot(
    root: Path, *, pr_number: int, commit_sha: str
) -> ModelOccEligibilityInput:
    return ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=pr_number,
        pr_title=f"fix({TICKET}): per-entry hashing",
        pr_body=f"Closes: {TICKET}",
        pr_branch=f"jonah/{TICKET.lower()}-x",
        pr_commit_shas=(commit_sha,),
        pr_commit_texts=(f"fix({TICKET}): work",),
        occ_commit_sha="b" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=root / "receipts",
    )


# --------------------------------------------------------------------------- #
# Determinism (scope 3a)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_entry_hash_deterministic_across_yamlfmt_reflow() -> None:
    contract = _contract(["a", "b"])
    baseline = compute_contract_entry_sha256(contract, "a")
    # yamlfmt-style transform that preserves parsed semantics:
    # reorder top-level keys, reorder nested keys, add a reworded title.
    reflowed = {
        "title": "COMPLETELY reworded title >- folded",
        "dod_evidence": [
            {
                "checks": [{"check_value": "cmd-a", "check_type": "command"}],
                "description": "entry a",
                "id": "a",
            },
            _entry("b", "cmd-b"),
        ],
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
    }
    assert compute_contract_entry_sha256(reflowed, "a") == baseline


# --------------------------------------------------------------------------- #
# Class 1 — append non-destructive
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_append_entry_does_not_invalidate_prior_receipts_eligibility(
    tmp_path: Path,
) -> None:
    # Grown contract [a, b, c]. a/b bound to PRIOR merged PRs; c bound to THIS PR.
    contract = _contract(["a", "b", "c"])
    _write_contract(tmp_path, contract)
    for item, pr, sha in (("a", 101, "a" * 40), ("b", 102, "b" * 40)):
        _write_receipt(
            tmp_path,
            item,
            _receipt_dict(
                item_id=item,
                pr_number=pr,
                commit_sha=sha,
                contract_entry_sha256=compute_contract_entry_sha256(contract, item),
            ),
        )
    this_sha = "c" * 40
    prior_a_bytes = (tmp_path / "receipts" / TICKET / "a" / "command.yaml").read_bytes()
    _write_receipt(
        tmp_path,
        "c",
        _receipt_dict(
            item_id="c",
            pr_number=303,
            commit_sha=this_sha,
            contract_entry_sha256=compute_contract_entry_sha256(contract, "c"),
        ),
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha=this_sha)
    )
    assert result.eligible is True, result.detail
    # prior receipt bytes untouched
    assert (
        tmp_path / "receipts" / TICKET / "a" / "command.yaml"
    ).read_bytes() == prior_a_bytes


@pytest.mark.unit
def test_append_entry_receipt_gate_passes_without_rewrite(tmp_path: Path) -> None:
    contract = _contract(["a", "b"])
    contract_path = _write_contract(tmp_path, contract)
    for item, pr, sha in (("a", 101, "a" * 40), ("b", 202, "b" * 40)):
        _write_receipt(
            tmp_path,
            item,
            _receipt_dict(
                item_id=item,
                pr_number=pr,
                commit_sha=sha,
                contract_entry_sha256=compute_contract_entry_sha256(contract, item),
            ),
        )
    result = validate_pr_receipts(
        pr_body=f"Closes: {TICKET}",
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
        pr_title=f"fix({TICKET}): x",
        pr_opened_at=parse_pr_opened_at("2026-06-01T00:00:00Z"),
        current_pr_number=202,
    )
    assert result.passed is True, result.message
    assert contract_path.exists()


# --------------------------------------------------------------------------- #
# Class 3 — forgery + grandfather + dual-accept
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_forged_entry_hash_fails_eligibility(tmp_path: Path) -> None:
    contract = _contract(["a"])
    _write_contract(tmp_path, contract)
    forged = "sha256:" + "0" * 64
    _write_receipt(
        tmp_path,
        "a",
        _receipt_dict(
            item_id="a",
            pr_number=303,
            commit_sha="c" * 40,
            contract_entry_sha256=forged,
        ),
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha="c" * 40)
    )
    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH


@pytest.mark.unit
def test_legacy_prior_receipt_grandfathered_on_grown_contract(tmp_path: Path) -> None:
    # a: legacy whole-file receipt bound to a PRIOR merged PR. b: current-PR
    # receipt with per-entry hash. The whole-file hash of the grown [a,b]
    # contract differs from a's recorded (stale) contract_sha256, but a is a
    # prior receipt so it is grandfathered (not re-hashed).
    contract = _contract(["a", "b"])
    _write_contract(tmp_path, contract)
    stale_whole = "sha256:" + "f" * 64
    _write_receipt(
        tmp_path,
        "a",
        _receipt_dict(
            item_id="a",
            pr_number=101,
            commit_sha="a" * 40,
            contract_sha256=stale_whole,
        ),
    )
    this_sha = "c" * 40
    _write_receipt(
        tmp_path,
        "b",
        _receipt_dict(
            item_id="b",
            pr_number=303,
            commit_sha=this_sha,
            contract_entry_sha256=compute_contract_entry_sha256(contract, "b"),
        ),
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha=this_sha)
    )
    assert result.eligible is True, result.detail


@pytest.mark.unit
def test_entry_hash_wins_over_stale_whole_file(tmp_path: Path) -> None:
    contract = _contract(["a"])
    _write_contract(tmp_path, contract)
    this_sha = "c" * 40
    _write_receipt(
        tmp_path,
        "a",
        _receipt_dict(
            item_id="a",
            pr_number=303,
            commit_sha=this_sha,
            contract_entry_sha256=compute_contract_entry_sha256(contract, "a"),
            contract_sha256="sha256:" + "f" * 64,  # stale whole-file, ignored
        ),
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha=this_sha)
    )
    assert result.eligible is True, result.detail


@pytest.mark.unit
def test_wrong_entry_hash_wins_over_matching_whole_file(tmp_path: Path) -> None:
    contract = _contract(["a"])
    contract_path = _write_contract(tmp_path, contract)
    this_sha = "c" * 40
    _write_receipt(
        tmp_path,
        "a",
        _receipt_dict(
            item_id="a",
            pr_number=303,
            commit_sha=this_sha,
            contract_entry_sha256="sha256:" + "0" * 64,  # wrong entry hash
            contract_sha256=_whole_file_hash(contract_path),  # matching whole-file
        ),
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha=this_sha)
    )
    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH


@pytest.mark.unit
def test_both_bindings_absent_hard_fails(tmp_path: Path) -> None:
    contract = _contract(["a"])
    _write_contract(tmp_path, contract)
    _write_receipt(
        tmp_path,
        "a",
        _receipt_dict(item_id="a", pr_number=303, commit_sha="c" * 40),
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha="c" * 40)
    )
    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH


# --------------------------------------------------------------------------- #
# Class 2 — supersession + tombstone
# --------------------------------------------------------------------------- #


def _supersession_dict(
    *, item_id: str, tombstone: bool, replacement: dict | None
) -> dict:
    data = {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": item_id,
        "check_type": "command",
        "supersedes": f"drift/dod_receipts/{TICKET}/{item_id}/command.yaml",
        "reason": "rebind to the actually-merged PR",
        "superseder": "closeout-agent",
        "created_at": datetime(2026, 6, 2, 12, 0, tzinfo=UTC),
        "tombstone": tombstone,
    }
    if replacement is not None:
        data["replacement"] = replacement
    return data


@pytest.mark.unit
def test_supersession_replacement_rebinds_key_eligibility(tmp_path: Path) -> None:
    contract = _contract(["a"])
    _write_contract(tmp_path, contract)
    # base receipt binds a stale/superseded PR
    _write_receipt(
        tmp_path,
        "a",
        _receipt_dict(
            item_id="a",
            pr_number=101,
            commit_sha="a" * 40,
            contract_entry_sha256=compute_contract_entry_sha256(contract, "a"),
        ),
    )
    this_sha = "c" * 40
    replacement = _receipt_dict(
        item_id="a",
        pr_number=303,
        commit_sha=this_sha,
        contract_entry_sha256=compute_contract_entry_sha256(contract, "a"),
    )
    supersede_path = (
        tmp_path / "receipts" / TICKET / "a" / "command.supersede.0001.yaml"
    )
    supersede_path.write_text(
        yaml.safe_dump(
            _supersession_dict(item_id="a", tombstone=False, replacement=replacement),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha=this_sha)
    )
    assert result.eligible is True, result.detail


@pytest.mark.unit
def test_tombstone_only_invalidates_key(tmp_path: Path) -> None:
    contract = _contract(["a"])
    _write_contract(tmp_path, contract)
    _write_receipt(
        tmp_path,
        "a",
        _receipt_dict(
            item_id="a",
            pr_number=303,
            commit_sha="c" * 40,
            contract_entry_sha256=compute_contract_entry_sha256(contract, "a"),
        ),
    )
    supersede_path = (
        tmp_path / "receipts" / TICKET / "a" / "command.supersede.0001.yaml"
    )
    supersede_path.write_text(
        yaml.safe_dump(
            _supersession_dict(item_id="a", tombstone=True, replacement=None),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    result = validate_occ_merge_eligibility(
        _snapshot(tmp_path, pr_number=303, commit_sha="c" * 40)
    )
    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_RECEIPT


@pytest.mark.unit
def test_highest_nnnn_untombstones(tmp_path: Path) -> None:
    contract = _contract(["a"])
    _write_contract(tmp_path, contract)
    key_dir = tmp_path / "receipts" / TICKET / "a"
    key_dir.mkdir(parents=True, exist_ok=True)
    (key_dir / "command.yaml").write_text("placeholder: true\n", encoding="utf-8")
    (key_dir / "command.supersede.0001.yaml").write_text(
        yaml.safe_dump(
            _supersession_dict(item_id="a", tombstone=True, replacement=None),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    replacement = _receipt_dict(
        item_id="a",
        pr_number=303,
        commit_sha="c" * 40,
        contract_entry_sha256=compute_contract_entry_sha256(contract, "a"),
    )
    (key_dir / "command.supersede.0002.yaml").write_text(
        yaml.safe_dump(
            _supersession_dict(item_id="a", tombstone=False, replacement=replacement),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    resolution = resolve_supersession(tmp_path / "receipts", TICKET, "a", "command")
    assert resolution is not None
    assert resolution.tombstoned is False
    assert resolution.receipt is not None
    assert resolution.receipt.pr_number == 303


# --------------------------------------------------------------------------- #
# Supersession model invariants
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_supersession_requires_replacement_unless_tombstone() -> None:
    with pytest.raises(ValueError, match="must carry a replacement"):
        ModelReceiptSupersession.model_validate(
            _supersession_dict(item_id="a", tombstone=False, replacement=None)
        )


@pytest.mark.unit
def test_supersession_replacement_must_carry_entry_hash() -> None:
    contract = _contract(["a"])
    replacement = _receipt_dict(
        item_id="a",
        pr_number=303,
        commit_sha="c" * 40,
        contract_sha256="sha256:" + "a" * 64,  # whole-file only, no entry hash
    )
    with pytest.raises(ValueError, match="contract_entry_sha256"):
        ModelReceiptSupersession.model_validate(
            _supersession_dict(item_id="a", tombstone=False, replacement=replacement)
        )
    del contract  # silence unused


@pytest.mark.unit
def test_supersession_tombstone_rejects_replacement() -> None:
    contract = _contract(["a"])
    replacement = _receipt_dict(
        item_id="a",
        pr_number=303,
        commit_sha="c" * 40,
        contract_entry_sha256=compute_contract_entry_sha256(contract, "a"),
    )
    with pytest.raises(ValueError, match="must not carry a replacement"):
        ModelReceiptSupersession.model_validate(
            _supersession_dict(item_id="a", tombstone=True, replacement=replacement)
        )


@pytest.mark.unit
def test_supersession_replacement_key_must_match() -> None:
    contract = _contract(["a", "b"])
    replacement = _receipt_dict(
        item_id="b",  # mismatched key
        pr_number=303,
        commit_sha="c" * 40,
        contract_entry_sha256=compute_contract_entry_sha256(contract, "b"),
    )
    with pytest.raises(ValueError, match="does not match"):
        ModelReceiptSupersession.model_validate(
            _supersession_dict(item_id="a", tombstone=False, replacement=replacement)
        )


# --------------------------------------------------------------------------- #
# Append-only validator
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_append_only_allows_new_entry() -> None:
    base = _contract(["a"])
    head = _contract(["a", "b"])
    result = evaluate_append_only(base, head, [])
    assert result.ok is True, result.detail


@pytest.mark.unit
def test_append_only_rejects_edit() -> None:
    base = _contract(["a"])
    head = _contract(["a"])
    # mutate entry a's check_value
    head["dod_evidence"][0]["checks"][0]["check_value"] = "MUTATED"
    result = evaluate_append_only(base, head, [])
    assert result.ok is False
    assert result.reason == "APPEND_ONLY_VIOLATION"
    assert result.violations[0].kind.value == "entry_edited"


@pytest.mark.unit
def test_append_only_rejects_removal() -> None:
    base = _contract(["a", "b"])
    head = _contract(["a"])
    result = evaluate_append_only(base, head, [])
    assert result.ok is False
    assert any(v.kind.value == "entry_removed" for v in result.violations)


@pytest.mark.unit
def test_append_only_rejects_receipt_file_mutation() -> None:
    base = _contract(["a"])
    head = _contract(["a"])
    diff = [("M", f"drift/dod_receipts/{TICKET}/a/command.yaml")]
    result = evaluate_append_only(base, head, diff)
    assert result.ok is False
    assert any(v.kind.value == "receipt_file_mutated" for v in result.violations)


@pytest.mark.unit
def test_append_only_allows_added_supersede_file() -> None:
    base = _contract(["a"])
    head = _contract(["a"])
    diff = [("A", f"drift/dod_receipts/{TICKET}/a/command.supersede.0001.yaml")]
    result = evaluate_append_only(base, head, diff)
    assert result.ok is True, result.detail


@pytest.mark.unit
def test_append_only_net_new_contract_passes() -> None:
    head = _contract(["a"])
    result = evaluate_append_only(None, head, [])
    assert result.ok is True
