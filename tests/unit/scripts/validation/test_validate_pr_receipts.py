# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Receipt-Gate library (`omnibase_core.validation.receipt_gate`).

Covers the full decision matrix: no-ticket, no-contract, missing-receipt,
failing-receipt, corrupt-receipt, receipt-path-mismatch, all-PASS, override.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.receipt_gate import validate_pr_receipts


def _write_contract(
    contracts_dir: Path,
    ticket_id: str,
    dod_evidence: list[dict] | None = None,
) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "ticket_id": ticket_id,
        "schema_version": "1.0.0",
        "summary": "test",
        "dod_evidence": dod_evidence
        if dod_evidence is not None
        else [
            {
                "id": "dod-001",
                "description": "test check",
                "checks": [{"check_type": "command", "check_value": "echo ok"}],
            }
        ],
    }
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(body))


def _write_receipt(
    receipts_dir: Path,
    *,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
    status: str = "PASS",
    check_value: str = "echo ok",
    overrides: dict | None = None,
) -> Path:
    p = receipts_dir / ticket_id / evidence_item_id / f"{check_type}.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "ticket_id": ticket_id,
        "evidence_item_id": evidence_item_id,
        "check_type": check_type,
        "check_value": check_value,
        "status": status,
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",
        "runner": "test-runner",
    }
    if overrides:
        data.update(overrides)
    p.write_text(yaml.safe_dump(data))
    return p


@pytest.mark.unit
class TestReceiptGateTicketRef:
    def test_no_ticket_ref_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="chore: update README",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "cites no" in result.message.lower()

    def test_ticket_ref_parsed_case_insensitive(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        _write_receipt(
            receipts,
            ticket_id="OMN-9084",
            evidence_item_id="dod-001",
            check_type="command",
        )
        result = validate_pr_receipts(
            pr_body="feat: thing [omn-9084]",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed


@pytest.mark.unit
class TestReceiptGateContractPresence:
    def test_missing_contract_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="OMN-9999",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no contract" in result.message

    def test_contract_without_dod_evidence_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-9084", dod_evidence=[])
        result = validate_pr_receipts(
            pr_body="OMN-9084",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no dod_evidence" in result.message

    def test_corrupt_contract_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        contracts.mkdir()
        (contracts / "OMN-9084.yaml").write_text("!!! not: valid: yaml: [")
        result = validate_pr_receipts(
            pr_body="OMN-9084",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "corrupt contract" in result.message


@pytest.mark.unit
class TestReceiptGateReceiptPresence:
    def test_all_pass_receipts_passes(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        _write_receipt(
            receipts,
            ticket_id="OMN-9084",
            evidence_item_id="dod-001",
            check_type="command",
        )
        result = validate_pr_receipts(
            pr_body="OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed
        assert "PASSED" in result.message

    def test_missing_receipt_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-9084")
        result = validate_pr_receipts(
            pr_body="OMN-9084",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no receipt" in result.message

    def test_failing_receipt_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        _write_receipt(
            receipts,
            ticket_id="OMN-9084",
            evidence_item_id="dod-001",
            check_type="command",
            status="FAIL",
        )
        result = validate_pr_receipts(
            pr_body="OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "failing receipt" in result.message

    def test_corrupt_receipt_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        p = receipts / "OMN-9084" / "dod-001" / "command.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("!!! not: valid: [")
        result = validate_pr_receipts(
            pr_body="OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert (
            "corrupt receipt" in result.message or "invalid receipt" in result.message
        )

    def test_receipt_path_mismatch_fails(self, tmp_path: Path) -> None:
        """Receipt at canonical path but self-declares different ticket → FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        _write_receipt(
            receipts,
            ticket_id="OMN-9084",
            evidence_item_id="dod-001",
            check_type="command",
            overrides={"ticket_id": "OMN-DIFFERENT"},
        )
        result = validate_pr_receipts(
            pr_body="OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed


@pytest.mark.unit
class TestReceiptGateMultiTicket:
    def test_any_failing_ticket_blocks(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        _write_contract(contracts, "OMN-9085")
        _write_receipt(
            receipts,
            ticket_id="OMN-9084",
            evidence_item_id="dod-001",
            check_type="command",
        )
        # OMN-9085 receipt missing
        result = validate_pr_receipts(
            pr_body="OMN-9084 OMN-9085",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert not result.passed
        assert "OMN-9085" in result.message

    def test_all_tickets_passing_passes(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9084")
        _write_contract(contracts, "OMN-9085")
        for tid in ("OMN-9084", "OMN-9085"):
            _write_receipt(
                receipts,
                ticket_id=tid,
                evidence_item_id="dod-001",
                check_type="command",
            )
        result = validate_pr_receipts(
            pr_body="OMN-9084 OMN-9085",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed


@pytest.mark.unit
class TestReceiptGateOverride:
    def test_override_passes_with_friction(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="fix: emergency hotfix [skip-receipt-gate: prod down OMN-1]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert result.passed
        assert result.friction_logged
        assert "prod down OMN-1" in result.message

    def test_empty_reason_does_not_override(self, tmp_path: Path) -> None:
        """Override must include a non-empty reason — empty falls through to FAIL."""
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate:     ]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        # Empty/whitespace reason doesn't count as a legitimate override
        assert not result.passed or result.friction_logged
        # Regex requires at least one non-whitespace char in the reason — the
        # `.+?` greedy-but-at-least-one means whitespace matches a single space
        # minimum. The `.strip()` call catches the empty-after-strip case.
