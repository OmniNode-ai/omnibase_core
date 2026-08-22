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
from omnibase_core.validation import validator_receipt_gate_cli
from omnibase_core.validation.validator_receipt_gate_cli import (
    _escape_github_actions_message,
)

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
        assert kwargs["target_branch"] == "dev"
        assert kwargs["receipt_gate_policy_mode"] == "dev-preflight"
        assert kwargs["occ_source_kind"] == "open-pr"
        return ModelReceiptGateResult(passed=True, message="ok")

    monkeypatch.setattr(
        validator_receipt_gate_cli,
        "validate_pr_receipts",
        fake_validate_pr_receipts,
    )

    assert (
        validator_receipt_gate_cli.main(
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
                "--target-branch",
                "dev",
                "--receipt-gate-policy-mode",
                "dev-preflight",
                "--occ-source-kind",
                "open-pr",
            ]
        )
        == 0
    )


def test_cli_rejects_pr_opened_at_without_timezone() -> None:
    """PR-opened timestamps must be timezone-aware for deterministic cutoff checks."""
    with pytest.raises(SystemExit) as exc_info:
        validator_receipt_gate_cli.main(
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

    exit_code = validator_receipt_gate_cli.main(
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


# ---------------------------------------------------------------------------
# OMN-16140 cross-boundary seam test.
#
# SEAM: the receipt-gate caller workflow
# (onex_change_control/.github/workflows/call-receipt-gate.yml) reads each
# commit message on the PR head into /tmp/pr_commit_texts.txt and passes them
# to this CLI as one repeated `--pr-commit-text <message>` flag per commit.
# The CLI parses them into `args.pr_commit_texts` (list[str] | None), coerces
# to a tuple, and hands them to `validate_pr_receipts(pr_commit_texts=...)`,
# which forwards them to `_verify_ticket_identity(commit_texts=...)` as the
# alternative satisfaction path for axis-2 identity binding.
#
# Field-by-field seam definition:
#   workflow arg    : --pr-commit-text            (repeated, one per commit)
#   argparse dest   : pr_commit_texts             (action="append", default None)
#   gate kwarg      : pr_commit_texts: tuple[str, ...]
#   identity kwarg  : commit_texts: tuple[str, ...]
#
# These tests drive that whole path through `main(argv)` with the literal flag
# strings the workflow emits — deliberately NOT two independent unit suites on
# either side of the boundary, which is the failure mode where both halves are
# individually green and the seam is a runtime no-op.
# ---------------------------------------------------------------------------


def _seam_write_contract(contracts_dir: Path, ticket_id: str) -> None:
    contracts_dir.mkdir(parents=True, exist_ok=True)
    (contracts_dir / f"{ticket_id}.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "ticket_id": ticket_id,
                "summary": "seam fixture",
                "dod_evidence": [
                    {
                        "id": "dod-001",
                        "description": "seam check",
                        "checks": [{"check_type": "command", "check_value": "echo ok"}],
                    }
                ],
            }
        )
    )


def _seam_write_receipt(receipts_dir: Path, ticket_id: str) -> None:
    p = receipts_dir / ticket_id / "dod-001" / "command.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(
            {
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
        )
    )


def _seam_argv(contracts: Path, receipts: Path, ticket: str) -> list[str]:
    """The exact flag shape the caller workflow emits, minus commit texts."""
    return [
        "--pr-body",
        f"Closes {ticket}\n\nEvidence-Source: abc1234\nEvidence-Ticket: {ticket}",
        "--pr-title",
        f"build({ticket}): retroactively ticketed change",
        "--contracts-dir",
        str(contracts),
        "--receipts-dir",
        str(receipts),
        # Branch predates the ticket and cannot reference it — the live shape of
        # omnibase_infra#2766 and onex_change_control#6500.
        "--branch-name",
        "jonah/omn-forwarder-delegation-worker",
    ]


def test_seam_commit_text_flags_reach_identity_binding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Driving the real CLI argv with --pr-commit-text must satisfy axis 2.

    This is the seam assertion: if the flag stops being parsed, stops being
    forwarded, or the receiving kwarg is renamed on either side, this fails.
    """
    contracts = tmp_path / "contracts"
    receipts = tmp_path / "receipts"
    _seam_write_contract(contracts, "OMN-10420")
    _seam_write_receipt(receipts, "OMN-10420")

    exit_code = validator_receipt_gate_cli.main(
        [
            *_seam_argv(contracts, receipts, "OMN-10420"),
            "--pr-commit-text",
            "chore: unrelated first commit",
            "--pr-commit-text",
            "bind evidence to OMN-10420 after retroactive filing",
        ]
    )

    assert exit_code == 0, capsys.readouterr().out


def test_seam_without_commit_text_flags_still_fails_axis_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Negative control for the seam: the identical invocation WITHOUT the
    commit-text flags must still fail, proving the flags are load-bearing and
    the positive case above is not passing for some unrelated reason."""
    contracts = tmp_path / "contracts"
    receipts = tmp_path / "receipts"
    _seam_write_contract(contracts, "OMN-10420")
    _seam_write_receipt(receipts, "OMN-10420")

    exit_code = validator_receipt_gate_cli.main(
        _seam_argv(contracts, receipts, "OMN-10420")
    )

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "IDENTITY BINDING FAILED" in out
    assert "commit message" in out.lower()


def test_seam_commit_text_flag_is_optional_for_existing_callers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Interlock guard: this CLI change must land BEFORE the workflow starts
    passing the flag, so a caller that does not yet pass it has to keep working
    with axis-2 behaviour byte-identical to before."""
    contracts = tmp_path / "contracts"
    receipts = tmp_path / "receipts"
    _seam_write_contract(contracts, "OMN-10420")
    _seam_write_receipt(receipts, "OMN-10420")

    argv = _seam_argv(contracts, receipts, "OMN-10420")
    argv[argv.index("--branch-name") + 1] = "jonah/omn-10420-correctly-named-branch"

    exit_code = validator_receipt_gate_cli.main(argv)

    assert exit_code == 0, capsys.readouterr().out
