# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Focused tests for the central PASS/FAIL decision matrix of validate_pr_receipts.

Covers the high-CCN paths in validator_receipt_gate.py that are not exercised
by the more specialised test files (adversarial, sha256, evidence-source,
identity-binding, skip-token):

- No ticket reference in PR body → FAIL
- Ticket with missing contract file → FAIL
- Ticket with corrupt contract YAML → FAIL
- Contract with no dod_evidence → FAIL
- Receipt missing on disk → FAIL
- Corrupt receipt YAML → FAIL
- Schema-invalid receipt (malformed YAML that parses, but fails Pydantic) → FAIL
- PASS receipt on disk → PASS
- Multiple tickets, all PASS → PASS
- Multiple tickets, one FAIL → FAIL
- _check_ticket: non-list dod_evidence → FAIL (contract-level)
- parse_evidence_source: OCC#NNN and SHA forms

Preserves deterministic-truth doctrine: the only accepted proof is a
PASS receipt with verifier ≠ runner, non-empty probe_command/probe_stdout.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validation.validator_receipt_gate import (
    parse_evidence_source,
    validate_pr_receipts,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_contract(
    contracts_dir: Path,
    ticket_id: str,
    dod_evidence: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write a minimal ticket contract YAML to disk."""
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body: dict[str, Any] = {
        "ticket_id": ticket_id,
        "schema_version": "1.0.0",
        "summary": "test contract",
    }
    if dod_evidence is not None:
        body["dod_evidence"] = dod_evidence
    if extra:
        body.update(extra)
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(body))


def _write_receipt(
    receipts_dir: Path,
    ticket_id: str,
    evidence_item_id: str,
    check_type: str,
    status: str = "PASS",
    verifier: str = "ci-bot",
    runner: str = "pytest-runner",
    probe_command: str = "uv run pytest",
    probe_stdout: str = "1 passed",
    check_value: str = "echo ok",
) -> None:
    """Write a PASS/FAIL receipt YAML at the canonical path.

    All required ModelDodReceipt fields are included so the receipt passes
    schema validation inside validate_pr_receipts. The commit_sha is a
    hard-coded 12-char hex string (valid git short-SHA per the validator).
    """
    receipt_dir = receipts_dir / ticket_id / evidence_item_id
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt: dict[str, Any] = {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
        "evidence_item_id": evidence_item_id,
        "check_type": check_type,
        "check_value": check_value,
        "status": status,
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": runner,
        "verifier": verifier,
        "probe_command": probe_command,
        "probe_stdout": probe_stdout,
    }
    (receipt_dir / f"{check_type}.yaml").write_text(yaml.safe_dump(receipt))


def _pr_body(ticket: str, closing: bool = True) -> str:
    """Generate a PR body that references a ticket."""
    if closing:
        return f"Closes: {ticket}\n\nThis PR implements the work."
    return f"Work for {ticket}."


# ---------------------------------------------------------------------------
# No-ticket-reference paths
# ---------------------------------------------------------------------------


class TestNoTicketReference:
    """validate_pr_receipts returns FAIL when no OMN-XXXX ticket is cited."""

    def test_empty_body_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no OMN-XXXX ticket" in result.message

    def test_body_without_ticket_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="Fixes a bug in the auth module.",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no OMN-XXXX ticket" in result.message

    def test_ticket_in_title_only_is_used_as_fallback(self, tmp_path: Path) -> None:
        """Title ticket extraction is the fallback when body has no closing keyword."""
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _write_contract(
            contracts_dir,
            "OMN-9999",
            dod_evidence=[
                {
                    "id": "dod-001",
                    "description": "test",
                    "checks": [{"check_type": "command", "check_value": "echo ok"}],
                }
            ],
        )
        _write_receipt(receipts_dir, "OMN-9999", "dod-001", "command")
        result = validate_pr_receipts(
            pr_body="No closing keyword here.",
            pr_title="feat(OMN-9999): add feature",
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert result.passed, result.message


# ---------------------------------------------------------------------------
# Contract-level failure paths
# ---------------------------------------------------------------------------


class TestContractLevelFailures:
    """validate_pr_receipts FAILs on contract-level issues before checking receipts."""

    def test_missing_contract_file_fails(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir(parents=True)
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-1001"),
            contracts_dir=contracts_dir,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no contract" in result.message

    def test_corrupt_contract_yaml_fails(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        contracts_dir.mkdir(parents=True)
        (contracts_dir / "OMN-1002.yaml").write_text(": invalid: [yaml\n")
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-1002"),
            contracts_dir=contracts_dir,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "corrupt contract" in result.message

    def test_contract_with_no_dod_evidence_fails(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        _write_contract(contracts_dir, "OMN-1003")
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-1003"),
            contracts_dir=contracts_dir,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no dod_evidence" in result.message

    def test_contract_with_non_list_dod_evidence_fails(self, tmp_path: Path) -> None:
        """A dod_evidence field that is not a list is treated as empty."""
        contracts_dir = tmp_path / "contracts"
        _write_contract(contracts_dir, "OMN-1004", extra={"dod_evidence": "bad"})
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-1004"),
            contracts_dir=contracts_dir,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no dod_evidence" in result.message

    def test_contract_with_empty_dod_evidence_list_fails(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        _write_contract(contracts_dir, "OMN-1005", dod_evidence=[])
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-1005"),
            contracts_dir=contracts_dir,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no dod_evidence" in result.message


# ---------------------------------------------------------------------------
# Receipt-level failure paths
# ---------------------------------------------------------------------------


class TestReceiptLevelFailures:
    """validate_pr_receipts FAILs when the receipt itself is missing or broken."""

    def _one_check_contract(self, contracts_dir: Path, ticket_id: str) -> None:
        _write_contract(
            contracts_dir,
            ticket_id,
            dod_evidence=[
                {
                    "id": "dod-001",
                    "description": "test",
                    "checks": [{"check_type": "command", "check_value": "echo ok"}],
                }
            ],
        )

    def test_missing_receipt_fails(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        self._one_check_contract(contracts_dir, "OMN-2001")
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-2001"),
            contracts_dir=contracts_dir,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no receipt" in result.message

    def test_corrupt_receipt_yaml_fails(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        self._one_check_contract(contracts_dir, "OMN-2002")
        receipt_dir = receipts_dir / "OMN-2002" / "dod-001"
        receipt_dir.mkdir(parents=True)
        (receipt_dir / "command.yaml").write_text(": bad [yaml\n")
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-2002"),
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert not result.passed
        assert "corrupt receipt" in result.message

    def test_receipt_wrong_ticket_id_fails(self, tmp_path: Path) -> None:
        """Receipt on disk declaring a different valid ticket_id than the PR → FAIL."""
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        self._one_check_contract(contracts_dir, "OMN-2003")
        _write_receipt(
            receipts_dir,
            "OMN-2003",
            "dod-001",
            "command",
        )
        # Overwrite with a different but valid OMN ticket_id so schema validation
        # passes but the path↔content mismatch check fires.
        receipt_path = receipts_dir / "OMN-2003" / "dod-001" / "command.yaml"
        data = yaml.safe_load(receipt_path.read_text())
        data["ticket_id"] = "OMN-9999"
        receipt_path.write_text(yaml.safe_dump(data))
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-2003"),
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert not result.passed
        # Gate surfaces the declared vs expected ticket_id mismatch
        assert "OMN-9999" in result.message or "ticket_id" in result.message

    def test_receipt_status_fail_rejected(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        self._one_check_contract(contracts_dir, "OMN-2004")
        _write_receipt(
            receipts_dir,
            "OMN-2004",
            "dod-001",
            "command",
            status="FAIL",
        )
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-2004"),
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert not result.passed

    def test_receipt_missing_verifier_fails(self, tmp_path: Path) -> None:
        """Receipt without verifier field is rejected by pre-schema adversarial guard."""
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        self._one_check_contract(contracts_dir, "OMN-2005")
        # Write a receipt that passes YAML parse but is missing the 'verifier' field.
        # The pre-schema guard in _check_one_receipt fires before Pydantic validation.
        receipt_dir = receipts_dir / "OMN-2005" / "dod-001"
        receipt_dir.mkdir(parents=True)
        (receipt_dir / "command.yaml").write_text(
            yaml.safe_dump(
                {
                    "schema_version": "1.0.0",
                    "ticket_id": "OMN-2005",
                    "evidence_item_id": "dod-001",
                    "check_type": "command",
                    "check_value": "echo ok",
                    "status": "PASS",
                    "run_timestamp": datetime.now(tz=UTC).isoformat(),
                    "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
                    "runner": "pytest-runner",
                    # 'verifier' intentionally omitted
                    "probe_command": "uv run pytest",
                    "probe_stdout": "1 passed",
                }
            )
        )
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-2005"),
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert not result.passed
        assert "verifier" in result.message


# ---------------------------------------------------------------------------
# PASS paths
# ---------------------------------------------------------------------------


class TestPassPaths:
    """validate_pr_receipts returns PASS when all receipts are valid."""

    def test_single_ticket_single_check_passes(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _write_contract(
            contracts_dir,
            "OMN-3001",
            dod_evidence=[
                {
                    "id": "dod-001",
                    "description": "test",
                    "checks": [{"check_type": "command", "check_value": "echo ok"}],
                }
            ],
        )
        _write_receipt(receipts_dir, "OMN-3001", "dod-001", "command")
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-3001"),
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert result.passed, result.message
        assert "PASS" in result.message
        assert result.tickets_checked == ["OMN-3001"]
        assert len(result.checks) == 1
        assert result.checks[0].passed

    def test_single_ticket_multiple_checks_all_pass(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _write_contract(
            contracts_dir,
            "OMN-3002",
            dod_evidence=[
                {
                    "id": "dod-001",
                    "description": "test1",
                    "checks": [
                        {"check_type": "command", "check_value": "echo ok"},
                        {"check_type": "coverage", "check_value": ">= 60%"},
                    ],
                }
            ],
        )
        _write_receipt(receipts_dir, "OMN-3002", "dod-001", "command")
        _write_receipt(receipts_dir, "OMN-3002", "dod-001", "coverage")
        result = validate_pr_receipts(
            pr_body=_pr_body("OMN-3002"),
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert result.passed, result.message
        assert len(result.checks) == 2

    def test_multiple_tickets_all_pass(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        for ticket in ("OMN-3010", "OMN-3011"):
            _write_contract(
                contracts_dir,
                ticket,
                dod_evidence=[
                    {
                        "id": "dod-001",
                        "description": "test",
                        "checks": [{"check_type": "command", "check_value": "echo ok"}],
                    }
                ],
            )
            _write_receipt(receipts_dir, ticket, "dod-001", "command")
        # Both tickets in one body
        pr_body = "Closes: OMN-3010\nCloses: OMN-3011\n"
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert result.passed, result.message
        assert len(result.tickets_checked) == 2

    def test_multiple_tickets_one_missing_contract_fails(self, tmp_path: Path) -> None:
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _write_contract(
            contracts_dir,
            "OMN-3020",
            dod_evidence=[
                {
                    "id": "dod-001",
                    "description": "test",
                    "checks": [{"check_type": "command", "check_value": "echo ok"}],
                }
            ],
        )
        _write_receipt(receipts_dir, "OMN-3020", "dod-001", "command")
        # OMN-3021 has no contract
        pr_body = "Closes: OMN-3020\nCloses: OMN-3021\n"
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert not result.passed
        # At least one check belongs to OMN-3021 and failed
        failed = [c for c in result.checks if not c.passed]
        assert any(c.ticket_id == "OMN-3021" for c in failed)


# ---------------------------------------------------------------------------
# parse_evidence_source
# ---------------------------------------------------------------------------


class TestParseEvidenceSource:
    """Unit tests for parse_evidence_source — OCC PR and SHA forms."""

    def test_occ_pr_form_parsed(self) -> None:
        pr_body = "Evidence-Source: OCC#1234\n"
        occ_pr, sha = parse_evidence_source(pr_body)
        assert occ_pr == "1234"
        assert sha is None

    def test_sha_form_parsed(self) -> None:
        sha_val = "a" * 40
        pr_body = f"Evidence-Source: {sha_val}\n"
        occ_pr, sha = parse_evidence_source(pr_body)
        assert occ_pr is None
        assert sha == sha_val

    def test_short_sha_7_chars_parsed(self) -> None:
        short_sha = "abc1234"
        pr_body = f"Evidence-Source: {short_sha}\n"
        occ_pr, sha = parse_evidence_source(pr_body)
        assert occ_pr is None
        assert sha == short_sha

    def test_no_evidence_source_returns_none_none(self) -> None:
        pr_body = "Some PR body without evidence source.\n"
        occ_pr, sha = parse_evidence_source(pr_body)
        assert occ_pr is None
        assert sha is None

    def test_invalid_evidence_source_returns_none_none(self) -> None:
        pr_body = "Evidence-Source: not-valid-format!!!\n"
        occ_pr, sha = parse_evidence_source(pr_body)
        assert occ_pr is None
        assert sha is None

    def test_case_insensitive_matching(self) -> None:
        pr_body = "EVIDENCE-SOURCE: OCC#5678\n"
        occ_pr, sha = parse_evidence_source(pr_body)
        assert occ_pr == "5678"
        assert sha is None


# ---------------------------------------------------------------------------
# OCC evidence lookup (policy mode: dev-preflight)
# ---------------------------------------------------------------------------


class TestOCCEvidenceLookup:
    """Tests for receipt gate in dev-preflight policy mode with Evidence-Source."""

    def test_evidence_source_without_evidence_ticket_fails(
        self, tmp_path: Path
    ) -> None:
        """Evidence-Source present but Evidence-Ticket missing → FAIL."""
        contracts_dir = tmp_path / "contracts"
        receipts_dir = tmp_path / "receipts"
        _write_contract(
            contracts_dir,
            "OMN-4001",
            dod_evidence=[
                {
                    "id": "dod-001",
                    "description": "test",
                    "checks": [{"check_type": "command", "check_value": "echo ok"}],
                }
            ],
        )
        _write_receipt(receipts_dir, "OMN-4001", "dod-001", "command")
        pr_body = (
            "Closes: OMN-4001\nEvidence-Source: OCC#9999\n"
            # No Evidence-Ticket line
        )
        result = validate_pr_receipts(
            pr_body=pr_body,
            contracts_dir=contracts_dir,
            receipts_dir=receipts_dir,
        )
        assert not result.passed
        assert "Evidence-Ticket" in result.message

    def test_unknown_policy_mode_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="Closes: OMN-9999\n",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            receipt_gate_policy_mode="unknown-mode",
        )
        assert not result.passed
        assert "Unknown receipt_gate_policy_mode" in result.message
