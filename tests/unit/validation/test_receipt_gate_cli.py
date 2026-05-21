# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Receipt-Gate CLI."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from omnibase_core.models.contracts.ticket.model_receipt_gate_result import (
    ModelReceiptGateResult,
)
from omnibase_core.validation import receipt_gate_cli
from omnibase_core.validation.receipt_gate_cli import _escape_github_actions_message

pytestmark = pytest.mark.unit


def test_escape_github_actions_message_payload() -> None:
    """Workflow command payloads must escape percent and line separators."""
    message = "PASS: OMN-1/dod-001/command (/tmp/r.yaml): 50%\r\nnext"

    assert (
        _escape_github_actions_message(message)
        == "PASS: OMN-1/dod-001/command (/tmp/r.yaml): 50%25%0D%0Anext"
    )


def test_cli_accepts_workflow_context_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Receipt-gate workflow context flags must not break older validation paths."""

    def fake_validate_pr_receipts(**kwargs: object) -> ModelReceiptGateResult:
        assert kwargs["pr_body"] == "Implements OMN-1"
        assert kwargs["pr_title"] == "feat: test"
        assert kwargs["pr_opened_at"] == datetime(2026, 5, 21, 12, 30, tzinfo=UTC)
        return ModelReceiptGateResult(passed=True, message="ok")

    monkeypatch.setattr(
        receipt_gate_cli,
        "validate_pr_receipts",
        fake_validate_pr_receipts,
    )

    assert (
        receipt_gate_cli.main(
            [
                "--pr-body",
                "Implements OMN-1",
                "--pr-title",
                "feat: test",
                "--contracts-dir",
                "contracts",
                "--receipts-dir",
                "receipts",
                "--current-repo",
                "omnibase_core",
                "--allowlist-path",
                "allowlists/skip_token_approvals.yaml",
                "--pr-author",
                "jonahgabriel",
                "--current-pr-number",
                "1024",
                "--pr-opened-at",
                "2026-05-21T12:30:00Z",
            ]
        )
        == 0
    )


def test_cli_rejects_pr_opened_at_without_timezone() -> None:
    """PR-opened timestamps must be timezone-aware for deterministic cutoff checks."""
    with pytest.raises(SystemExit) as exc_info:
        receipt_gate_cli.main(
            [
                "--pr-body",
                "Implements OMN-1",
                "--contracts-dir",
                "contracts",
                "--receipts-dir",
                "receipts",
                "--pr-opened-at",
                "2026-05-21T12:30:00",
            ]
        )

    assert exc_info.value.code == 2


def test_cli_enforces_post_cutoff_contract_sha256(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI must pass PR-opened time into the gate so hash binding is enforced."""
    contracts_dir = tmp_path / "contracts"
    receipts_dir = tmp_path / "receipts"
    receipt_path = receipts_dir / "OMN-10421" / "dod-001" / "command.yaml"
    contracts_dir.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)
    (contracts_dir / "OMN-10421.yaml").write_text(
        yaml.safe_dump(
            {
                "ticket_id": "OMN-10421",
                "schema_version": "1.0.0",
                "summary": "hash binding",
                "dod_evidence": [
                    {
                        "id": "dod-001",
                        "description": "command check",
                        "checks": [{"check_type": "command", "check_value": "echo ok"}],
                    }
                ],
            }
        )
    )
    receipt_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "ticket_id": "OMN-10421",
                "evidence_item_id": "dod-001",
                "check_type": "command",
                "check_value": "echo ok",
                "status": "PASS",
                "run_timestamp": datetime(2026, 5, 21, 12, 30, tzinfo=UTC),
                "commit_sha": "a1b2c3d4",
                "runner": "ci",
                "verifier": "reviewer",
                "probe_command": "echo ok",
                "probe_stdout": "ok\n",
            }
        )
    )

    exit_code = receipt_gate_cli.main(
        [
            "--pr-body",
            "Closes OMN-10421",
            "--contracts-dir",
            str(contracts_dir),
            "--receipts-dir",
            str(receipts_dir),
            "--pr-opened-at",
            "2026-05-21T12:30:00Z",
        ]
    )

    assert exit_code == 1
    assert "contract_sha256" in capsys.readouterr().out
