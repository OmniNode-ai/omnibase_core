# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression tests for legacy and per-PR OCC contract layouts (OMN-20068)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest
import yaml

from omnibase_core.enums.ticket.enum_receipt_status import EnumReceiptStatus
from omnibase_core.handlers.handler_occ_contract_view import (
    legacy_contract_path,
    load_occ_contract_view,
    per_pr_contract_path,
)
from omnibase_core.validation.validator_occ_merge_eligibility import (
    EnumOccEligibilityReason,
    ModelOccEligibilityInput,
    validate_occ_merge_eligibility,
)
from omnibase_core.validation.validator_receipt_gate import (
    _CONTRACT_SHA256_REQUIRED_AFTER,
    compute_contract_entry_sha256,
    validate_pr_receipts,
)

TICKET = "OMN-20068"
PR_SHA = "1" * 40
type Layout = Literal["legacy-only", "per-PR-only", "mixed"]
LAYOUTS: tuple[Layout, ...] = ("legacy-only", "per-PR-only", "mixed")
RECEIPT_IDS = (f"{TICKET}:dod-a:command", f"{TICKET}:dod-b:command")


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _write_contract(
    path: Path, item_ids: tuple[str, ...], *, ticket_id: str = TICKET
) -> None:
    data = {
        "ticket_id": ticket_id,
        "schema_version": "1.0.0",
        "title": "OCC contract layout tests",
        "dod_evidence": [
            {
                "id": item_id,
                "description": f"probe {item_id}",
                "checks": [
                    {"check_type": "command", "check_value": f"probe {item_id}"}
                ],
            }
            for item_id in item_ids
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")


def _write_receipt(
    root: Path,
    *,
    evidence_item_id: str,
    contract_sha256: str,
    contract_entry_sha256: str | None = None,
) -> None:
    receipt: dict[str, object] = {
        "schema_version": "1.0.0",
        "ticket_id": TICKET,
        "evidence_item_id": evidence_item_id,
        "check_type": "command",
        "check_value": f"probe {evidence_item_id}",
        "status": EnumReceiptStatus.PASS.value,
        "run_timestamp": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "commit_sha": PR_SHA,
        "runner": "worker",
        "verifier": "foreground",
        "probe_command": f"probe {evidence_item_id}",
        "probe_stdout": "1 passed\n",
        "exit_code": 0,
        "pr_number": 123,
        "contract_sha256": contract_sha256,
    }
    if contract_entry_sha256 is not None:
        receipt["contract_entry_sha256"] = contract_entry_sha256
    path = root / "receipts" / TICKET / evidence_item_id / "command.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(receipt, sort_keys=True), encoding="utf-8")


def _write_bound_receipt(root: Path, path: Path, item_id: str) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _write_receipt(
        root,
        evidence_item_id=item_id,
        contract_sha256=_sha256(path),
        contract_entry_sha256=compute_contract_entry_sha256(data, item_id),
    )


def _build_layout(root: Path, layout: Layout) -> dict[str, Path]:
    """Write the same entries and bound PASS receipts in each supported layout."""
    contracts = root / "contracts"
    legacy = legacy_contract_path(contracts, TICKET)
    first = per_pr_contract_path(contracts, TICKET, "omnibase_core", 101)
    second = per_pr_contract_path(contracts, TICKET, "omnimarket", 202)
    if layout == "legacy-only":
        entries_by_file: dict[Path, tuple[str, ...]] = {legacy: ("dod-a", "dod-b")}
    elif layout == "per-PR-only":
        entries_by_file = {first: ("dod-a",), second: ("dod-b",)}
    else:
        entries_by_file = {legacy: ("dod-a",), second: ("dod-b",)}

    sources: dict[str, Path] = {}
    for path, item_ids in entries_by_file.items():
        _write_contract(path, item_ids)
        for item_id in item_ids:
            sources[item_id] = path
            _write_bound_receipt(root, path, item_id)
    return sources


def _snapshot(root: Path) -> ModelOccEligibilityInput:
    return ModelOccEligibilityInput(
        repo="omnibase_core",
        pr_number=123,
        pr_title=f"feat({TICKET}): add per-PR OCC contracts",
        pr_body=f"Closes: {TICKET}",
        pr_branch=f"jonah/{TICKET.lower()}-occ-contract-layouts",
        pr_commit_shas=(PR_SHA,),
        pr_commit_texts=(f"feat({TICKET}): add contract layout tests",),
        occ_commit_sha="b" * 40,
        contracts_dir=root / "contracts",
        receipts_dir=root / "receipts",
    )


@pytest.mark.unit
@pytest.mark.parametrize("layout", LAYOUTS)
def test_loader_unions_entries_and_tracks_sources(
    tmp_path: Path, layout: Layout
) -> None:
    sources = _build_layout(tmp_path, layout)

    view = load_occ_contract_view(tmp_path / "contracts", TICKET)

    assert view is not None
    assert isinstance(view.data, dict)
    assert {item["id"] for item in view.data["dod_evidence"]} == {"dod-a", "dod-b"}
    for item_id, path in sources.items():
        assert view.source_for(item_id).path == path
    if layout == "legacy-only":
        assert view.data == yaml.safe_load(sources["dod-a"].read_text(encoding="utf-8"))


@pytest.mark.unit
@pytest.mark.parametrize("layout", LAYOUTS)
def test_eligibility_and_receipt_ids_match_across_layouts(
    tmp_path: Path, layout: Layout
) -> None:
    _build_layout(tmp_path, layout)

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is True, result.detail
    assert result.receipt_ids == RECEIPT_IDS


@pytest.mark.unit
@pytest.mark.parametrize("layout", LAYOUTS)
def test_receipt_gate_passes_each_layout(tmp_path: Path, layout: Layout) -> None:
    _build_layout(tmp_path, layout)

    result = validate_pr_receipts(
        pr_body=f"Closes: {TICKET}",
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
        pr_opened_at=_CONTRACT_SHA256_REQUIRED_AFTER,
    )

    assert result.passed is True, result.message


@pytest.mark.unit
@pytest.mark.parametrize(
    "violation", ["wrong-ticket", "duplicate-id", "invalid-name", "empty-evidence"]
)
def test_invalid_companion_is_a_missing_contract(
    tmp_path: Path,
    violation: Literal[
        "wrong-ticket", "duplicate-id", "invalid-name", "empty-evidence"
    ],
) -> None:
    sources = _build_layout(tmp_path, "mixed")
    companion = sources["dod-b"]
    if violation == "wrong-ticket":
        _write_contract(companion, ("dod-b",), ticket_id="OMN-1")
    elif violation == "duplicate-id":
        _write_contract(companion, ("dod-a",))
    elif violation == "invalid-name":
        companion.rename(companion.with_name("notes.yaml"))
    else:
        _write_contract(companion, ())

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.MISSING_CONTRACT


@pytest.mark.unit
def test_receipt_hash_of_another_file_is_ineligible(tmp_path: Path) -> None:
    sources = _build_layout(tmp_path, "per-PR-only")
    assert _sha256(sources["dod-a"]) != _sha256(sources["dod-b"])
    _write_receipt(
        tmp_path,
        evidence_item_id="dod-a",
        contract_sha256=_sha256(sources["dod-b"]),
    )

    result = validate_occ_merge_eligibility(_snapshot(tmp_path))

    assert result.eligible is False
    assert result.reason is EnumOccEligibilityReason.CONTRACT_HASH_MISMATCH


@pytest.mark.unit
def test_receipt_gate_rejects_companion_with_wrong_ticket(tmp_path: Path) -> None:
    sources = _build_layout(tmp_path, "per-PR-only")
    _write_contract(sources["dod-b"], ("dod-b",), ticket_id="OMN-1")
    _write_bound_receipt(tmp_path, sources["dod-b"], "dod-b")

    result = validate_pr_receipts(
        pr_body=f"Closes: {TICKET}",
        contracts_dir=tmp_path / "contracts",
        receipts_dir=tmp_path / "receipts",
        pr_opened_at=_CONTRACT_SHA256_REQUIRED_AFTER,
    )

    assert result.passed is False


@pytest.mark.unit
def test_appending_companion_preserves_existing_files_and_eligibility(
    tmp_path: Path,
) -> None:
    sources = _build_layout(tmp_path, "per-PR-only")
    before = {path: (path.read_bytes(), _sha256(path)) for path in sources.values()}
    initial = validate_occ_merge_eligibility(_snapshot(tmp_path))
    assert initial.eligible is True, initial.detail

    companion = per_pr_contract_path(tmp_path / "contracts", TICKET, "omniclaude", 303)
    _write_contract(companion, ("dod-c",))
    _write_bound_receipt(tmp_path, companion, "dod-c")

    for path, (content, digest) in before.items():
        assert path.read_bytes() == content
        assert _sha256(path) == digest
    result = validate_occ_merge_eligibility(_snapshot(tmp_path))
    assert result.eligible is True, result.detail
    assert result.receipt_ids == (*RECEIPT_IDS, f"{TICKET}:dod-c:command")


@pytest.mark.unit
def test_contract_paths_are_distinct_and_use_short_repo_names(tmp_path: Path) -> None:
    contracts = tmp_path / "contracts"
    first = per_pr_contract_path(contracts, TICKET, "OmniNode-ai/omnibase_core", 101)
    second = per_pr_contract_path(contracts, TICKET, "omnimarket", 202)
    legacy = legacy_contract_path(contracts, TICKET)

    assert len({first, second, legacy}) == 3
    assert first.parent == contracts / TICKET
    assert second.parent == contracts / TICKET
    assert first.name == "omnibase_core-101.yaml"
    assert second.name == "omnimarket-202.yaml"
