# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-10347/OMN-10417: Receipt-Gate [skip-*] token hardening tests.

Rule #10 (CLAUDE.md): ANY [skip-*] bypass token in a PR body must FAIL the
receipt gate unless it is the central-allowlist receipt-gate form
``[skip-receipt-gate: <approval-id>]`` with a valid scoped allowlist entry.

Previously the gate accepted [skip-receipt-gate:] with only a warning (exit 0).
This test suite verifies that:
  - [skip-receipt-gate:] alone FAILs
  - [skip-deploy-gate:] alone FAILs (regression)
  - [skip-anything-else:] alone FAILs
  - Legacy inline '# skip-token-allowed: <id>' does not bypass the gate
  - A clean PR body with a ticket and receipts still PASSes
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.receipt_gate import (
    ALLOWLIST_PATTERN,
    OVERRIDE_PATTERN,
    SKIP_TOKEN_PATTERN,
    validate_pr_receipts,
)

pytestmark = pytest.mark.unit


# ──────────────────────────────────────────────────────────────────────────────
# Pattern unit tests
# ──────────────────────────────────────────────────────────────────────────────


class TestSkipTokenPattern:
    """Verify SKIP_TOKEN_PATTERN matches all [skip-*] variants."""

    def test_matches_skip_receipt_gate(self) -> None:
        assert SKIP_TOKEN_PATTERN.search("[skip-receipt-gate: docs only]")

    def test_matches_skip_deploy_gate(self) -> None:
        assert SKIP_TOKEN_PATTERN.search("[skip-deploy-gate: correctness fix]")

    def test_matches_skip_anything(self) -> None:
        assert SKIP_TOKEN_PATTERN.search("[skip-anything: some reason]")

    def test_no_match_on_clean_body(self) -> None:
        assert not SKIP_TOKEN_PATTERN.search("Closes OMN-9999\nNormal PR body.")

    def test_no_match_on_placeholder_example(self) -> None:
        assert not SKIP_TOKEN_PATTERN.search("[skip-receipt-gate: <token>]")

    def test_case_insensitive_skip_receipt_gate(self) -> None:
        assert SKIP_TOKEN_PATTERN.search("[Skip-Receipt-Gate: reason]")

    def test_case_insensitive_skip_deploy_gate(self) -> None:
        assert SKIP_TOKEN_PATTERN.search("[SKIP-DEPLOY-GATE: reason]")

    def test_override_pattern_matches_receipt_gate_approval_id(self) -> None:
        match = OVERRIDE_PATTERN.search("[skip-receipt-gate: appr-001]")
        assert match is not None
        assert match.group(1) == "appr-001"

    def test_override_pattern_rejects_free_text(self) -> None:
        assert not OVERRIDE_PATTERN.search("[skip-receipt-gate: docs only]")

    def test_override_pattern_does_not_match_other_skip_tokens(self) -> None:
        assert not OVERRIDE_PATTERN.search("[skip-deploy-gate: appr-001]")


class TestAllowlistPattern:
    """Verify legacy inline approval marker parsing remains stable."""

    def test_matches_escape_hatch(self) -> None:
        assert ALLOWLIST_PATTERN.search(
            "# skip-token-allowed: USER-APPROVAL-2026-04-30"
        )

    def test_no_match_on_empty_receipt_id(self) -> None:
        assert not ALLOWLIST_PATTERN.search("# skip-token-allowed:")

    def test_no_match_on_whitespace_only_receipt_id(self) -> None:
        assert not ALLOWLIST_PATTERN.search("# skip-token-allowed:   ")

    def test_case_insensitive(self) -> None:
        assert ALLOWLIST_PATTERN.search("# Skip-Token-Allowed: some-receipt")


# ──────────────────────────────────────────────────────────────────────────────
# Gate integration tests — no contracts/receipts on disk needed for skip-token
# paths because the skip-token check fires before ticket resolution.
# ──────────────────────────────────────────────────────────────────────────────


def _empty_dir(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir()
    return d


class TestSkipReceiptGateTokenFails:
    """[skip-*] tokens without a central allowlist approval must FAIL the gate."""

    def test_skip_receipt_gate_alone_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: docs only, no receipts needed]",
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        assert not result.passed
        assert (
            "skip-*" in result.message or "skip-receipt-gate" in result.message.lower()
        )

    def test_skip_deploy_gate_alone_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="[skip-deploy-gate: correctness fix, no deployable artifact]",
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        assert not result.passed
        assert (
            "skip-*" in result.message or "skip-deploy-gate" in result.message.lower()
        )

    def test_skip_anything_alone_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="[skip-anything: arbitrary reason]",
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        assert not result.passed

    def test_case_insensitive_skip_fails(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="[Skip-Receipt-Gate: reason here]",
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        assert not result.passed

    def test_rule10_mentioned_in_failure_message(self, tmp_path: Path) -> None:
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: some reason]",
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        assert not result.passed
        msg_lower = result.message.lower()
        assert "allowlist" in msg_lower or "approval-id" in msg_lower


class TestInlineSkipTokenAllowedDoesNotBypass:
    """Legacy '# skip-token-allowed' marker is not an approval mechanism."""

    def test_skip_receipt_gate_with_inline_marker_fails(self, tmp_path: Path) -> None:
        body = (
            "[skip-receipt-gate: chore only]\n"
            "# skip-token-allowed: USER-APPROVAL-2026-04-30-jonah"
        )
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        assert not result.passed
        assert not result.friction_logged
        assert "allowlist token" in result.message

    def test_skip_deploy_gate_with_inline_marker_fails(self, tmp_path: Path) -> None:
        body = (
            "[skip-deploy-gate: correctness fix]\n"
            "# skip-token-allowed: USER-APPROVAL-2026-04-25-jonah"
        )
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        assert not result.passed
        assert not result.friction_logged
        assert "allowlist token" in result.message

    def test_allowlist_with_empty_receipt_id_still_fails(self, tmp_path: Path) -> None:
        body = "[skip-receipt-gate: reason]\n# skip-token-allowed:"
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
        )
        # No valid receipt ID → FAIL
        assert not result.passed


# ──────────────────────────────────────────────────────────────────────────────
# Regression: clean PR with proper ticket + receipt still passes
# ──────────────────────────────────────────────────────────────────────────────


def _write_contract(contracts_dir: Path, ticket_id: str) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "ticket_id": ticket_id,
        "schema_version": "1.0.0",
        "summary": "test",
        "dod_evidence": [
            {
                "id": "dod-001",
                "description": "test check",
                "checks": [{"check_type": "command", "check_value": "echo ok"}],
            }
        ],
    }
    (contracts_dir / f"{ticket_id}.yaml").write_text(yaml.safe_dump(body))


def _write_pass_receipt(receipts_dir: Path, ticket_id: str) -> None:
    p = receipts_dir / ticket_id / "dod-001" / "command.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": "1.0.0",
        "ticket_id": ticket_id,
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
    p.write_text(yaml.safe_dump(receipt))


class TestCleanPrStillPasses:
    """A clean PR body with a valid ticket + receipts must still pass."""

    def test_clean_pr_passes(self, tmp_path: Path) -> None:
        contracts = tmp_path / "contracts"
        receipts = tmp_path / "receipts"
        _write_contract(contracts, "OMN-9999")
        _write_pass_receipt(receipts, "OMN-9999")

        result = validate_pr_receipts(
            pr_body="Closes OMN-9999\n\nFixes the thing.",
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed
        assert not result.friction_logged
