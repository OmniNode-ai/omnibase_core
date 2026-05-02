# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ticket-identity binding tests for receipt-gate (OMN-10420).

Five cases as required by the plan (T6b):
    1. missing_evidence_ticket   — no Evidence-Ticket line → FAIL
    2. pr_title_mismatch         — PR title references different ticket → FAIL
    3. branch_mismatch           — branch name references different ticket → FAIL
    4. contract_ticket_id_mismatch — contract ticket_id field ≠ Evidence-Ticket → FAIL
    5. receipt_ticket_id_mismatch  — receipt ticket_id field ≠ Evidence-Ticket → FAIL

Each failure message must identify the specific axis that mismatched.
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
    *,
    contract_ticket_id: str | None = None,
    include_ticket_id: bool = True,
) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "schema_version": "1.0.0",
        "summary": "test contract for identity binding",
        "dod_evidence": [
            {
                "id": "dod-001",
                "description": "identity check",
                "checks": [{"check_type": "command", "check_value": "echo ok"}],
            }
        ],
    }
    if include_ticket_id:
        body["ticket_id"] = (
            contract_ticket_id if contract_ticket_id is not None else ticket_id
        )
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(body))


def _write_receipt(
    receipts_dir: Path,
    ticket_id: str,
    *,
    receipt_ticket_id: str | None = None,
) -> None:
    p = receipts_dir / ticket_id / "dod-001" / "command.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": "1.0.0",
        "ticket_id": receipt_ticket_id if receipt_ticket_id is not None else ticket_id,
        "evidence_item_id": "dod-001",
        "check_type": "command",
        "check_value": "echo ok",
        "status": "PASS",
        "run_timestamp": datetime.now(tz=UTC).isoformat(),
        "commit_sha": "a1b2c3d4e5f6",  # pragma: allowlist secret
        "runner": "worker-A",
        "verifier": "foreground-claude-X",
        "probe_command": "echo ok",
        "probe_stdout": "ok\n",
    }
    p.write_text(yaml.safe_dump(data))


@pytest.mark.unit
class TestTicketIdentityBinding:
    """Five required identity-binding failure cases (OMN-10420 / T6b)."""

    # Identity binding is triggered when Evidence-Source is present in the PR body
    # (T6a pairing) OR when evidence_ticket is explicitly passed to the gate.
    # All tests below use Evidence-Source in the PR body to activate binding.

    def test_missing_evidence_ticket_fails(self, tmp_path: Path) -> None:
        """Case 1: Evidence-Source present but no Evidence-Ticket line → FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n\n"
                "This PR implements the feature."
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        assert not result.passed
        msg_lower = result.message.lower()
        assert "evidence-ticket" in msg_lower, (
            f"message must mention 'Evidence-Ticket'; got: {result.message!r}"
        )

    def test_pr_title_mismatch_fails(self, tmp_path: Path) -> None:
        """Case 2: PR title references OMN-1234 but Evidence-Ticket is OMN-10420 → FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-1234): some other ticket entirely",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        assert not result.passed
        msg_lower = result.message.lower()
        assert "pr title" in msg_lower or "title" in msg_lower, (
            f"message must mention 'PR title'; got: {result.message!r}"
        )
        assert "omn-10420" in msg_lower or "omn-1234" in msg_lower

    def test_pr_title_partial_ticket_match_fails(self, tmp_path: Path) -> None:
        """PR title must contain the exact Evidence-Ticket token, not a prefix."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-104201): wrong ticket prefix",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        assert not result.passed
        assert "pr title" in result.message.lower()

    def test_branch_mismatch_fails(self, tmp_path: Path) -> None:
        """Case 3: branch references OMN-9999 but Evidence-Ticket is OMN-10420 → FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-9999-completely-different-ticket",
        )

        assert not result.passed
        msg_lower = result.message.lower()
        assert "branch" in msg_lower, (
            f"message must mention 'branch'; got: {result.message!r}"
        )
        assert "omn-9999" in msg_lower or "omn-10420" in msg_lower

    def test_branch_partial_ticket_match_fails(self, tmp_path: Path) -> None:
        """Branch name must contain the exact Evidence-Ticket token, not a prefix."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-104201-wrong-ticket-prefix",
        )

        assert not result.passed
        assert "branch" in result.message.lower()

    def test_contract_ticket_id_mismatch_fails(self, tmp_path: Path) -> None:
        """Case 4: contract ticket_id=OMN-5678 but Evidence-Ticket=OMN-10420 → FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        # Contract file is named OMN-10420.yaml but its ticket_id field says OMN-5678
        _write_contract(contracts, "OMN-10420", contract_ticket_id="OMN-5678")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        assert not result.passed
        msg_lower = result.message.lower()
        assert "contract" in msg_lower, (
            f"message must mention 'contract'; got: {result.message!r}"
        )
        assert "ticket_id" in msg_lower or "omn-5678" in msg_lower

    def test_contract_missing_ticket_id_fails(self, tmp_path: Path) -> None:
        """Case 4b: contract without ticket_id fails closed."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420", include_ticket_id=False)
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        assert not result.passed
        msg_lower = result.message.lower()
        assert "contract" in msg_lower
        assert "ticket_id" in msg_lower

    def test_receipt_ticket_id_mismatch_fails(self, tmp_path: Path) -> None:
        """Case 5: receipt ticket_id=OMN-9999 but Evidence-Ticket=OMN-10420 → FAIL."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        # Receipt lives under OMN-10420/ dir but its ticket_id field says OMN-9999
        _write_receipt(receipts, "OMN-10420", receipt_ticket_id="OMN-9999")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        assert not result.passed
        msg_lower = result.message.lower()
        assert "receipt" in msg_lower, (
            f"message must mention 'receipt'; got: {result.message!r}"
        )
        assert "ticket_id" in msg_lower or "omn-9999" in msg_lower

    def test_valid_identity_passes_gate(self, tmp_path: Path) -> None:
        """Sanity: all axes consistent → gate passes normally."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420"
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        assert result.passed, result.message

    def test_evidence_ticket_auto_detected_from_pr_body(self, tmp_path: Path) -> None:
        """Evidence-Ticket line is auto-detected when Evidence-Source is also present."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\n"
                "Evidence-Source: abc123\n"
                "Evidence-Ticket: OMN-10420\n\n"
                "Some body text."
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
            # evidence_ticket not passed — must be auto-detected from pr_body
        )

        assert result.passed, result.message

    def test_evidence_ticket_arg_overrides_body_detection(self, tmp_path: Path) -> None:
        """Explicit evidence_ticket= arg takes precedence over PR body detection."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10420\n\nEvidence-Source: abc123\nEvidence-Ticket: OMN-9999"
            ),
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
            evidence_ticket="OMN-10420",  # explicit arg wins; body says OMN-9999
        )

        assert result.passed, result.message

    def test_explicit_evidence_ticket_is_normalized(self, tmp_path: Path) -> None:
        """Explicit evidence_ticket arguments use canonical case for path lookups."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body="Closes OMN-10420\n\nEvidence-Source: abc123",
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
            evidence_ticket=" omn-10420 ",
        )

        assert result.passed, result.message

    def test_no_evidence_source_skips_identity_binding(self, tmp_path: Path) -> None:
        """Without Evidence-Source, identity binding is not triggered (pre-T6a compat)."""
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-10420")
        _write_receipt(receipts, "OMN-10420")

        result = validate_pr_receipts(
            pr_body="Closes OMN-10420\n\nNo Evidence-Source here.",
            pr_title="feat(OMN-10420): ticket identity binding",
            contracts_dir=contracts,
            receipts_dir=receipts,
            branch_name="jonah/omn-10420-ticket-identity-binding",
        )

        # Gate should proceed to receipt verification, not fail on missing Evidence-Ticket
        assert result.passed, result.message
