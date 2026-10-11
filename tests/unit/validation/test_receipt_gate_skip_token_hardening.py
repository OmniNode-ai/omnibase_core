# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-10347/OMN-20074: Receipt-Gate [skip-*] token hardening tests.

Rule #10 (CLAUDE.md): ANY [skip-*] bypass token in a PR body must FAIL the
receipt gate. The central approvals registry that once admitted
``[skip-receipt-gate: <approval-id>]`` is retired (OMN-20074), so no token form
passes, an approval-id-shaped one included.

This test suite verifies that:
  - [skip-receipt-gate:] alone FAILs, with free text or an approval-id-shaped id
  - [skip-deploy-gate:] alone FAILs (regression)
  - [skip-anything-else:] alone FAILs
  - A receipt-id comment ('# skip-token-allowed: <id>') never rescues a token
  - A clean PR body with a ticket and receipts still PASSes
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from inspect import signature
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.validator_receipt_gate import (
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
        assert "no bypass" in result.message.lower()

    def test_approval_id_shaped_token_fails(self, tmp_path: Path) -> None:
        """The registry that admitted an id-shaped token is retired (OMN-20074)."""
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-001]",
            contracts_dir=_empty_dir(tmp_path, "contracts"),
            receipts_dir=_empty_dir(tmp_path, "receipts"),
            pr_author="someone",
            current_repo="omnibase_core",
            current_pr_number=1,
        )
        assert not result.passed
        assert not result.friction_logged
        assert "no bypass" in result.message.lower()


def test_registry_approval_cannot_bypass_receipt_gate(tmp_path: Path) -> None:
    """An approval accepted before retirement must now fail the public gate."""
    approval_path = tmp_path / "approvals.yaml"
    approval_path.write_text(
        yaml.safe_dump(
            {
                "approvals": [
                    {
                        "id": "appr-retirement-control",
                        "granted_by": "independent-reviewer",
                        "expires_at": (
                            datetime.now(tz=UTC) + timedelta(days=1)
                        ).isoformat(),
                        "scope_repos": ["omnibase_core"],
                        "scope_pr_numbers": [1953],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    gate_signature = signature(validate_pr_receipts)
    request = gate_signature.bind(
        pr_body="[skip-receipt-gate: appr-retirement-control]",
        contracts_dir=_empty_dir(tmp_path, "contracts"),
        receipts_dir=_empty_dir(tmp_path, "receipts"),
        pr_author="pr-author",
        current_repo="omnibase_core",
        current_pr_number=1953,
    )
    # Give the merge-base control its real registry input when that API exists.
    # Both trees face the same rejection assertion, rather than a TypeError.
    if "allowlist_path" in gate_signature.parameters:
        request.arguments["allowlist_path"] = approval_path
    result = validate_pr_receipts(*request.args, **request.kwargs)

    assert not result.passed
    assert not result.friction_logged
    assert "no bypass" in result.message.lower()


class TestInlineSkipTokenAllowedDoesNotBypass:
    """A receipt-id comment ('# skip-token-allowed') never rescues a token."""

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
        assert "no bypass" in result.message.lower()

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
        assert "no bypass" in result.message.lower()

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
