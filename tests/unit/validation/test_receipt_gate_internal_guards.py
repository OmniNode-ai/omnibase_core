# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for validator_receipt_gate internal guard branches.

Covers high-CCN paths in validator_receipt_gate.py (CCN 33, 747 lines):
- _check_adversarial_invariants_raw: non-dict input, missing fields, empty fields
- _validate_skip_token: corrupt YAML allowlist, non-dict allowlist, non-list approvals
- _iter_dod_evidence: malformed contract structures
- _normalized_branch: refs/heads/ and heads/ prefix stripping
- _evidence_class_present: promotion / hotfix matching
- parse_pr_opened_at: timezone-naive and missing-timezone errors
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from omnibase_core.validation.validator_receipt_gate import (
    _check_adversarial_invariants_raw,
    _evidence_class_present,
    _iter_dod_evidence,
    _normalized_branch,
    _validate_skip_token,
    parse_pr_opened_at,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _check_adversarial_invariants_raw
# ---------------------------------------------------------------------------


class TestCheckAdversarialInvariantsRaw:
    """Direct tests for the pre-schema adversarial guard."""

    def _dummy_path(self) -> Path:
        return Path("/tmp/dummy/receipt.yaml")

    def test_non_dict_returns_none(self) -> None:
        result = _check_adversarial_invariants_raw("not a dict", self._dummy_path())
        assert result is None

    def test_non_dict_list_returns_none(self) -> None:
        result = _check_adversarial_invariants_raw([1, 2, 3], self._dummy_path())
        assert result is None

    def test_missing_verifier_field_returns_failure(self) -> None:
        raw = {
            "probe_command": "uv run pytest",
            "probe_stdout": "passed",
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is not None
        assert "verifier" in result

    def test_missing_probe_command_field_returns_failure(self) -> None:
        raw = {
            "verifier": "agent-x",
            "probe_stdout": "passed",
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is not None
        assert "probe_command" in result

    def test_missing_probe_stdout_field_returns_failure(self) -> None:
        raw = {
            "verifier": "agent-x",
            "probe_command": "uv run pytest",
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is not None
        assert "probe_stdout" in result

    def test_empty_verifier_returns_failure(self) -> None:
        raw = {
            "verifier": "   ",
            "probe_command": "uv run pytest",
            "probe_stdout": "passed",
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is not None
        assert "verifier" in result

    def test_empty_probe_command_returns_failure(self) -> None:
        raw = {
            "verifier": "agent-x",
            "probe_command": "",
            "probe_stdout": "passed",
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is not None
        assert "probe_command" in result

    def test_all_fields_present_and_non_empty_returns_none(self) -> None:
        raw = {
            "verifier": "agent-x",
            "probe_command": "uv run pytest",
            "probe_stdout": "",  # probe_stdout may be empty for non-exec check types
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is None

    def test_non_string_verifier_returns_failure(self) -> None:
        raw = {
            "verifier": 12345,
            "probe_command": "uv run pytest",
            "probe_stdout": "passed",
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is not None
        assert "verifier" in result

    def test_none_probe_command_returns_failure(self) -> None:
        raw = {
            "verifier": "agent-x",
            "probe_command": None,
            "probe_stdout": "passed",
        }
        result = _check_adversarial_invariants_raw(raw, self._dummy_path())
        assert result is not None
        assert "probe_command" in result


# ---------------------------------------------------------------------------
# _validate_skip_token: corrupt/malformed allowlist branches
# ---------------------------------------------------------------------------


def _future(days: int = 7) -> str:
    return (datetime.now(tz=UTC) + timedelta(days=days)).isoformat()


def _valid_entry(
    entry_id: str = "appr-001",
    granted_by: str = "platform-lead",
    repo: str = "omnibase_core",
    pr_num: int = 999,
) -> dict[object, object]:
    return {
        "id": entry_id,
        "granted_by": granted_by,
        "granted_at": "2026-04-30T00:00:00+00:00",
        "expires_at": _future(),
        "scope_repos": [repo],
        "scope_pr_numbers": [pr_num],
    }


class TestValidateSkipTokenMalformedAllowlist:
    """Tests for _validate_skip_token with corrupted or malformed allowlist files."""

    def test_corrupt_yaml_allowlist_returns_rejection(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        allowlist.write_text(": invalid: yaml: {{{{")
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="dev",
            current_repo="omnibase_core",
            current_pr_number=999,
            allowlist_path=allowlist,
        )
        assert not accepted
        assert "corrupt" in msg.lower() or "rejected" in msg.lower()

    def test_non_dict_allowlist_returns_rejection(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        allowlist.write_text("- just a list\n- not a mapping\n")
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="dev",
            current_repo="omnibase_core",
            current_pr_number=999,
            allowlist_path=allowlist,
        )
        assert not accepted
        assert "rejected" in msg.lower()

    def test_non_list_approvals_key_returns_rejection(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        allowlist.write_text("approvals: not-a-list\n")
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="dev",
            current_repo="omnibase_core",
            current_pr_number=999,
            allowlist_path=allowlist,
        )
        assert not accepted
        assert "rejected" in msg.lower()

    def test_missing_allowlist_file_returns_rejection(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "nonexistent.yaml"
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="dev",
            current_repo="omnibase_core",
            current_pr_number=999,
            allowlist_path=allowlist,
        )
        assert not accepted
        assert "not found" in msg.lower() or "rejected" in msg.lower()

    def test_valid_entry_not_found_returns_rejection(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        allowlist.write_text(yaml.safe_dump({"approvals": [_valid_entry("other-id")]}))
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="dev",
            current_repo="omnibase_core",
            current_pr_number=999,
            allowlist_path=allowlist,
        )
        assert not accepted
        assert "appr-001" in msg

    def test_unparseable_expires_at_returns_rejection(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        entry = dict(_valid_entry())
        entry["expires_at"] = "not-a-datetime"
        allowlist.write_text(yaml.safe_dump({"approvals": [entry]}))
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="dev",
            current_repo="omnibase_core",
            current_pr_number=999,
            allowlist_path=allowlist,
        )
        assert not accepted
        assert "rejected" in msg.lower()

    def test_none_expires_at_returns_rejection(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        entry = dict(_valid_entry())
        entry["expires_at"] = None
        allowlist.write_text(yaml.safe_dump({"approvals": [entry]}))
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="dev",
            current_repo="omnibase_core",
            current_pr_number=999,
            allowlist_path=allowlist,
        )
        assert not accepted
        assert "expires_at" in msg

    def test_pr_number_none_skips_pr_scope_check(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        allowlist.write_text(yaml.safe_dump({"approvals": [_valid_entry()]}))
        # current_pr_number=None means PR scope check is skipped
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="other-person",
            current_repo="omnibase_core",
            current_pr_number=None,
            allowlist_path=allowlist,
        )
        assert accepted
        assert "bypass accepted" in msg.lower()

    def test_repo_none_skips_repo_scope_check(self, tmp_path: Path) -> None:
        allowlist = tmp_path / "skip_token_approvals.yaml"
        allowlist.write_text(yaml.safe_dump({"approvals": [_valid_entry()]}))
        # current_repo=None means repo scope check is skipped
        accepted, msg = _validate_skip_token(
            approval_id="appr-001",
            pr_author="other-person",
            current_repo=None,
            current_pr_number=None,
            allowlist_path=allowlist,
        )
        assert accepted
        assert "bypass accepted" in msg.lower()


# ---------------------------------------------------------------------------
# _iter_dod_evidence: malformed contract data branches
# ---------------------------------------------------------------------------


class TestIterDodEvidence:
    """Tests for _iter_dod_evidence with malformed input."""

    def test_non_dict_contract_returns_empty(self) -> None:
        assert _iter_dod_evidence("not a dict") == []

    def test_list_contract_returns_empty(self) -> None:
        assert _iter_dod_evidence([{"id": "x"}]) == []

    def test_none_contract_returns_empty(self) -> None:
        assert _iter_dod_evidence(None) == []

    def test_missing_dod_evidence_key_returns_empty(self) -> None:
        assert _iter_dod_evidence({"ticket_id": "OMN-1234"}) == []

    def test_non_list_dod_evidence_returns_empty(self) -> None:
        contract = {"dod_evidence": "not a list"}
        assert _iter_dod_evidence(contract) == []

    def test_non_dict_item_in_dod_evidence_is_skipped(self) -> None:
        contract = {"dod_evidence": ["string item", {"id": "real-item", "checks": []}]}
        result = _iter_dod_evidence(contract)
        # "string item" is skipped; real-item has no checks → also skipped
        assert result == []

    def test_item_missing_id_is_skipped(self) -> None:
        contract = {
            "dod_evidence": [
                {"checks": [{"check_type": "unit_tests", "check_value": "pass"}]}
            ]
        }
        assert _iter_dod_evidence(contract) == []

    def test_item_with_non_list_checks_is_skipped(self) -> None:
        contract = {"dod_evidence": [{"id": "ev-1", "checks": "not a list"}]}
        assert _iter_dod_evidence(contract) == []

    def test_check_missing_check_type_is_skipped(self) -> None:
        contract = {
            "dod_evidence": [{"id": "ev-1", "checks": [{"check_value": "pass"}]}]
        }
        assert _iter_dod_evidence(contract) == []

    def test_check_missing_check_value_is_skipped(self) -> None:
        contract = {
            "dod_evidence": [{"id": "ev-1", "checks": [{"check_type": "unit_tests"}]}]
        }
        assert _iter_dod_evidence(contract) == []

    def test_check_non_string_check_type_is_skipped(self) -> None:
        contract = {
            "dod_evidence": [
                {"id": "ev-1", "checks": [{"check_type": 42, "check_value": "pass"}]}
            ]
        }
        assert _iter_dod_evidence(contract) == []

    def test_valid_contract_returns_expected_triples(self) -> None:
        contract = {
            "dod_evidence": [
                {
                    "id": "ev-1",
                    "checks": [
                        {"check_type": "unit_tests", "check_value": "pytest"},
                        {"check_type": "lint", "check_value": "ruff"},
                    ],
                },
                {
                    "id": "ev-2",
                    "checks": [{"check_type": "mypy", "check_value": "strict"}],
                },
            ]
        }
        result = _iter_dod_evidence(contract)
        assert result == [
            ("ev-1", "unit_tests", "pytest"),
            ("ev-1", "lint", "ruff"),
            ("ev-2", "mypy", "strict"),
        ]

    def test_mixed_valid_and_invalid_items(self) -> None:
        contract = {
            "dod_evidence": [
                "skip me",
                {
                    "id": "ev-1",
                    "checks": [{"check_type": "unit_tests", "check_value": "pytest"}],
                },
                {"missing_id": True, "checks": []},
            ]
        }
        result = _iter_dod_evidence(contract)
        assert result == [("ev-1", "unit_tests", "pytest")]


# ---------------------------------------------------------------------------
# _normalized_branch: refs/heads/ and heads/ prefix stripping
# ---------------------------------------------------------------------------


class TestNormalizedBranch:
    """Tests for _normalized_branch helper."""

    def test_none_returns_empty_string(self) -> None:
        assert _normalized_branch(None) == ""

    def test_bare_branch_name_unchanged(self) -> None:
        assert _normalized_branch("main") == "main"

    def test_refs_heads_prefix_stripped(self) -> None:
        assert _normalized_branch("refs/heads/main") == "main"

    def test_heads_prefix_stripped(self) -> None:
        assert _normalized_branch("heads/feature/x") == "feature/x"

    def test_refs_heads_on_feature_branch(self) -> None:
        assert (
            _normalized_branch("refs/heads/jonah/omn-1234-foo") == "jonah/omn-1234-foo"
        )

    def test_whitespace_stripped(self) -> None:
        assert _normalized_branch("  main  ") == "main"

    def test_dev_branch_unchanged(self) -> None:
        assert _normalized_branch("dev") == "dev"


# ---------------------------------------------------------------------------
# _evidence_class_present: promotion and hotfix detection
# ---------------------------------------------------------------------------


class TestEvidenceClassPresent:
    """Tests for _evidence_class_present helper."""

    def test_promotion_detected(self) -> None:
        body = "Evidence-Class: promotion\nsome other content"
        assert _evidence_class_present(body, "promotion") is True

    def test_hotfix_detected(self) -> None:
        body = "Evidence-Class: hotfix\n"
        assert _evidence_class_present(body, "hotfix") is True

    def test_wrong_class_returns_false(self) -> None:
        body = "Evidence-Class: promotion\n"
        assert _evidence_class_present(body, "hotfix") is False

    def test_absent_returns_false(self) -> None:
        assert _evidence_class_present("No evidence class here", "promotion") is False

    def test_case_insensitive_class(self) -> None:
        body = "Evidence-Class: PROMOTION\n"
        assert _evidence_class_present(body, "promotion") is True

    def test_multiple_evidence_class_lines_first_match_wins(self) -> None:
        body = "Evidence-Class: hotfix\nEvidence-Class: promotion\n"
        assert _evidence_class_present(body, "hotfix") is True
        assert _evidence_class_present(body, "promotion") is True


# ---------------------------------------------------------------------------
# parse_pr_opened_at: timezone and format error branches
# ---------------------------------------------------------------------------


class TestParsePrOpenedAt:
    """Tests for parse_pr_opened_at error branches."""

    def test_none_returns_none(self) -> None:
        assert parse_pr_opened_at(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_pr_opened_at("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_pr_opened_at("   ") is None

    def test_valid_utc_z_suffix_parsed(self) -> None:
        result = parse_pr_opened_at("2026-04-30T12:00:00Z")
        assert result is not None
        assert result.tzinfo is not None
        assert result.tzinfo == UTC

    def test_valid_offset_parsed(self) -> None:
        result = parse_pr_opened_at("2026-04-30T12:00:00+00:00")
        assert result is not None

    def test_invalid_format_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="ISO-8601"):
            parse_pr_opened_at("not-a-date")

    def test_naive_datetime_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            parse_pr_opened_at("2026-04-30T12:00:00")

    def test_result_is_utc(self) -> None:
        result = parse_pr_opened_at("2026-04-30T12:00:00+05:30")
        assert result is not None
        assert result.tzinfo == UTC
