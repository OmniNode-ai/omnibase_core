# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Receipt-Gate CLI."""

from __future__ import annotations

import pytest

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
            ]
        )
        == 0
    )
