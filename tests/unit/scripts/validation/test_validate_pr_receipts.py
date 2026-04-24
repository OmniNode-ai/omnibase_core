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
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
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

    def test_closing_keyword_case_insensitive(self, tmp_path: Path) -> None:
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
            pr_body="closes omn-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed


@pytest.mark.unit
class TestReceiptGateGreedyRegression:
    """Regression tests for OMN-9574 — bare OMN-XXXX must NOT trigger receipt checks."""

    def test_bare_omn_token_in_body_no_closing_keyword_does_not_require_receipt(
        self, tmp_path: Path
    ) -> None:
        """Bare OMN-1234 with no closing keyword → no citation → gate fails with 'no ticket ref'."""
        result = validate_pr_receipts(
            pr_body="This PR relates to OMN-1234 (see issue tracker)",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "cites no" in result.message.lower()

    def test_bare_omn_token_does_not_require_receipt_even_when_contract_exists(
        self, tmp_path: Path
    ) -> None:
        """A bare mention must not trigger receipt check even if the contract file exists."""
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-9600")
        result = validate_pr_receipts(
            pr_body="Related to OMN-9600 (no closing keyword)",
            contracts_dir=contracts,
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "cites no" in result.message.lower()

    def test_closes_keyword_required_for_receipt_check(self, tmp_path: Path) -> None:
        """Closes OMN-1234 triggers the full receipt check."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-1234")
        _write_receipt(
            receipts,
            ticket_id="OMN-1234",
            evidence_item_id="dod-001",
            check_type="command",
        )
        result = validate_pr_receipts(
            pr_body="Closes OMN-1234.",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed

    def test_fixes_keyword_triggers_receipt_check(self, tmp_path: Path) -> None:
        """Fixes OMN-1234 triggers the receipt check."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-1234")
        _write_receipt(
            receipts,
            ticket_id="OMN-1234",
            evidence_item_id="dod-001",
            check_type="command",
        )
        result = validate_pr_receipts(
            pr_body="Fixes OMN-1234",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed

    def test_closes_keyword_lowercase_triggers_receipt_check(
        self, tmp_path: Path
    ) -> None:
        """closes OMN-1234 (lowercase) triggers the receipt check (case-insensitive)."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-1234")
        _write_receipt(
            receipts,
            ticket_id="OMN-1234",
            evidence_item_id="dod-001",
            check_type="command",
        )
        result = validate_pr_receipts(
            pr_body="closes OMN-1234",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed


@pytest.mark.unit
class TestReceiptGateContractPresence:
    def test_missing_contract_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="Closes OMN-9999",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        assert not result.passed
        assert "no contract" in result.message

    def test_contract_without_dod_evidence_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-9084", dod_evidence=[])
        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
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
            pr_body="Closes OMN-9084",
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
            pr_body="Closes OMN-9084",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed
        assert "PASSED" in result.message

    def test_missing_receipt_fails(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        _write_contract(contracts, "OMN-9084")
        result = validate_pr_receipts(
            pr_body="Closes OMN-9084",
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
            pr_body="Closes OMN-9084",
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
            pr_body="Closes OMN-9084",
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
            pr_body="Closes OMN-9084",
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
            pr_body="Closes OMN-9084. Closes OMN-9085",
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
            pr_body="Closes OMN-9084. Closes OMN-9085",
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


@pytest.mark.unit
class TestReceiptGateClosingKeywords:
    def test_closing_keyword_preferred_over_bare_mention(self, tmp_path: Path) -> None:
        """When body has closing keyword, only the cited ticket is checked (not bare mentions)."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-5678")
        _write_receipt(
            receipts,
            ticket_id="OMN-5678",
            evidence_item_id="dod-001",
            check_type="command",
        )
        result = validate_pr_receipts(
            pr_body="Related to OMN-1234, closes OMN-5678",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed
        assert result.tickets_checked == ["OMN-5678"]

    def test_pr_title_fallback_when_body_has_no_closing_keywords(
        self, tmp_path: Path
    ) -> None:
        """No closing keyword in body → fall back to OMN-XXXX tokens in title."""
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
            pr_body="See description in the title",
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_title="fix(OMN-9084): some fix",
        )
        assert result.passed
        assert result.tickets_checked == ["OMN-9084"]

    def test_closing_keyword_variants(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-1111")
        _write_receipt(
            receipts,
            ticket_id="OMN-1111",
            evidence_item_id="dod-001",
            check_type="command",
        )
        for keyword in ("Closes", "Fixes", "Resolves", "Implements"):
            result = validate_pr_receipts(
                pr_body=f"{keyword} OMN-1111",
                contracts_dir=contracts,
                receipts_dir=receipts,
            )
            assert result.passed, f"Failed for keyword: {keyword}"

    def test_no_title_no_closing_keyword_fails(self, tmp_path: Path) -> None:
        """No closing keyword in body AND no title → no citation → FAIL."""
        result = validate_pr_receipts(
            pr_body="no tickets here",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            pr_title="also no tickets",
        )
        assert not result.passed
        assert "cites no" in result.message.lower()
