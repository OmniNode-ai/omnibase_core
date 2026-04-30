# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Skip-token allowlist tests for receipt-gate (OMN-10417).

Six cases as required by the plan:
    1. unknown_id       — id not found in allowlist → FAIL
    2. expired          — expires_at in the past → FAIL
    3. scope_mismatch_repo — current repo not in scope_repos → FAIL
    4. scope_mismatch_pr   — current PR not in scope_pr_numbers → FAIL
    5. self_approved    — granted_by == pr_author → FAIL
    6. valid            — all checks pass → PASS with friction_logged=True

Also tests:
    - free-text token (space in id) → FAIL (OVERRIDE_PATTERN rejects)
    - placeholder token (<token>) → falls through to ticket extraction
    - missing scope_pr_numbers → FAIL
    - no allowlist_path provided → FAIL
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.receipt_gate import validate_pr_receipts


def _write_allowlist(path: Path, entries: list[dict[object, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"approvals": entries}))


def _future(days: int = 7) -> str:
    return (datetime.now(tz=UTC) + timedelta(days=days)).isoformat()


def _past(days: int = 1) -> str:
    return (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()


def _valid_entry(
    *,
    entry_id: str = "appr-001",
    granted_by: str = "platform-lead",
    scope_repos: list[str] | None = None,
    scope_pr_numbers: list[int] | None = None,
    expires_at: str | None = None,
) -> dict[object, object]:
    return {
        "id": entry_id,
        "granted_by": granted_by,
        "granted_at": "2026-04-30T00:00:00+00:00",
        "expires_at": expires_at or _future(),
        "scope_repos": scope_repos or ["omnibase_core"],
        "scope_pr_numbers": scope_pr_numbers if scope_pr_numbers is not None else [999],
    }


@pytest.mark.unit
class TestSkipTokenAllowlist:
    """Six required cases for allowlist-authenticated skip token."""

    def test_unknown_id_fails(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(allowlist, [_valid_entry(entry_id="appr-001")])

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-999]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert not result.passed
        assert "appr-999" in result.message
        assert "not found" in result.message.lower()

    def test_expired_entry_fails(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [_valid_entry(entry_id="appr-expired", expires_at=_past(1))],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-expired]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert not result.passed
        assert "expired" in result.message.lower()
        assert "appr-expired" in result.message

    def test_scope_mismatch_repo_fails(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [_valid_entry(entry_id="appr-scoped", scope_repos=["omniclaude"])],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-scoped]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert not result.passed
        msg = result.message.lower()
        assert "scope" in msg or "repo" in msg

    def test_scope_mismatch_pr_fails(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [_valid_entry(entry_id="appr-pr-scoped", scope_pr_numbers=[111, 222])],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-pr-scoped]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert not result.passed
        assert "999" in result.message or "scope" in result.message.lower()

    def test_self_approved_fails(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [_valid_entry(entry_id="appr-self", granted_by="jonahgabriel")],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-self]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="jonahgabriel",
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert not result.passed
        msg = result.message.lower()
        assert "self" in msg or "self-approval" in msg or "jonahgabriel" in msg

    def test_self_approved_fails_case_insensitively(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [_valid_entry(entry_id="appr-self-case", granted_by="JonahGabriel")],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-self-case]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="jonahgabriel",
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert not result.passed
        assert "self" in result.message.lower()

    def test_valid_entry_passes_with_friction(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        _write_allowlist(
            allowlist,
            [
                _valid_entry(
                    entry_id="appr-valid",
                    granted_by="platform-lead",
                    scope_repos=["omnibase_core"],
                    scope_pr_numbers=[999],
                )
            ],
        )

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-valid]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            pr_author="worker-A",
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert result.passed, result.message
        assert result.friction_logged
        assert "appr-valid" in result.message
        assert "platform-lead" in result.message


@pytest.mark.unit
class TestSkipTokenEdgeCases:
    """Additional edge cases: free-text, missing scope_pr_numbers, no allowlist_path."""

    def test_free_text_reason_not_matched_by_override_pattern(
        self, tmp_path: Path
    ) -> None:
        """A token with spaces is not a bare identifier — OVERRIDE_PATTERN won't match it
        and the gate proceeds to ticket extraction (which finds no ticket → FAIL)."""
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: this is a free text reason]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )
        # OVERRIDE_PATTERN requires \S+ (no whitespace), so this doesn't match.
        # Falls through to ticket extraction → no ticket → FAIL.
        assert not result.passed
        assert "no omn" in result.message.lower() or "ticket" in result.message.lower()

    def test_placeholder_token_not_matched_by_override_pattern(
        self, tmp_path: Path
    ) -> None:
        result = validate_pr_receipts(
            pr_body=(
                "Closes OMN-10417. Documents the [skip-receipt-gate: <token>] syntax."
            ),
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
        )

        assert not result.message.startswith("[skip-receipt-gate]")

    def test_missing_scope_pr_numbers_in_entry_fails(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "allowlists" / "skip_token_approvals.yaml"
        entry: dict[object, object] = {
            "id": "appr-no-pr-scope",
            "granted_by": "platform-lead",
            "granted_at": "2026-04-30T00:00:00+00:00",
            "expires_at": _future(),
            "scope_repos": ["omnibase_core"],
            # scope_pr_numbers intentionally omitted
        }
        _write_allowlist(allowlist, [entry])

        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-no-pr-scope]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=allowlist,
            current_repo="omnibase_core",
            current_pr_number=999,
        )

        assert not result.passed
        assert "scope_pr_numbers" in result.message

    def test_no_allowlist_path_provided_fails(self, tmp_path: Path) -> None:
        """Skip token present but no allowlist_path → hard FAIL."""
        result = validate_pr_receipts(
            pr_body="[skip-receipt-gate: appr-001]",
            contracts_dir=tmp_path / "contracts",
            receipts_dir=tmp_path / "receipts",
            allowlist_path=None,
        )

        assert not result.passed
        assert (
            "allowlist" in result.message.lower()
            or "no allowlist" in result.message.lower()
        )
