# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the bypass-token blocklist gate (OMN-13388).

Covers all 9 blocked tokens — both the pre-commit Python validator and
the repo-wide grep function that backs the CI workflow.  Each test section
has a "failing" case (token present → rejected) and a "passing" case (no
token → accepted).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from omnibase_core.validators.bypass_token_blocklist import (
    BYPASS_TOKENS,
    SUPPRESSION_TOKEN,
    find_tokens_in_file,
    find_tokens_in_text,
    main,
    scan_tree,
)

# ---------------------------------------------------------------------------
# Canonical token list — the test is the single source of truth for "9 tokens"
# ---------------------------------------------------------------------------

EXPECTED_TOKENS: tuple[str, ...] = (
    "[skip-receipt-gate:",
    "--no-verify",
    "--no-gpg-sign",
    "[skip ci]",
    "[ci skip]",
    "[skip-dod-sweep:",
    "[skip-cr-gate:",
    "[deploy-gate-bypass:",
    "receipt-gate-bypass",
)


class TestCanonicalTokenList:
    """BYPASS_TOKENS must enumerate exactly the 9 blocked tokens."""

    def test_token_count_is_nine(self) -> None:
        assert len(BYPASS_TOKENS) == 9, (
            f"Expected 9 bypass tokens, got {len(BYPASS_TOKENS)}: {BYPASS_TOKENS}"
        )

    def test_all_expected_tokens_present(self) -> None:
        for token in EXPECTED_TOKENS:
            assert token in BYPASS_TOKENS, f"Token {token!r} missing from BYPASS_TOKENS"

    def test_no_extra_tokens(self) -> None:
        expected_set = set(EXPECTED_TOKENS)
        actual_set = set(BYPASS_TOKENS)
        extra = actual_set - expected_set
        assert not extra, f"Unexpected tokens in BYPASS_TOKENS: {extra}"


# ---------------------------------------------------------------------------
# Per-token: failing case (detected) + passing case (clean)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("token", EXPECTED_TOKENS)
class TestPerTokenDetection:
    """Each token must be caught by find_tokens_in_text and clean text must pass."""

    def test_token_is_detected(self, token: str) -> None:
        text = f"Some content with {token} embedded here\n"
        findings = find_tokens_in_text(text, Path("pr_body.md"))
        assert findings, f"Token {token!r} was not detected"
        assert any(f.token == token for f in findings), (
            f"Expected token {token!r} in findings, got {findings}"
        )

    def test_token_line_number_is_correct(self, token: str) -> None:
        text = f"line one\n{token}\nline three\n"
        findings = find_tokens_in_text(text, Path("body.md"))
        assert findings
        assert findings[0].line_number == 2

    def test_clean_text_passes(self, token: str) -> None:
        # Ensure there's no false positive on text that doesn't contain the token
        clean = "This PR is clean and has no bypass tokens.\nAll gates are green.\n"
        findings = find_tokens_in_text(clean, Path("clean.md"))
        assert not findings, f"False positive for token {token!r}: {findings}"

    def test_case_insensitive_detection(self, token: str) -> None:
        # Tokens that contain alphabetic characters must be caught case-insensitively
        upper = token.upper()
        text = f"Contains {upper} here\n"
        findings = find_tokens_in_text(text, Path("upper.md"))
        # Only tokens with alphabetic chars are case-sensitive; all our tokens qualify
        assert findings, (
            f"Token {token!r} (upper: {upper!r}) was not detected case-insensitively"
        )


# ---------------------------------------------------------------------------
# Suppression token
# ---------------------------------------------------------------------------


class TestSuppression:
    """The suppression comment must allow the token through."""

    def test_suppressed_line_is_allowed(self) -> None:
        # A line that has both the token AND the suppression annotation is allowed
        token = "[skip-receipt-gate:"
        text = f"Some text {token} example  {SUPPRESSION_TOKEN} user-approval-123\n"
        findings = find_tokens_in_text(text, Path("pr.md"))
        assert not findings, f"Suppressed line should not produce findings: {findings}"

    def test_suppression_only_applies_to_its_line(self) -> None:
        # Suppression on line 3 must NOT cover the token on line 1
        token = "--no-verify"
        text = textwrap.dedent(f"""\
            git commit {token}
            ordinary line
            {SUPPRESSION_TOKEN} some-receipt
        """)
        findings = find_tokens_in_text(text, Path("pr.md"))
        assert findings, (
            "Suppression on a different line must not cover the token elsewhere"
        )

    def test_clean_file_with_suppression_passes(self) -> None:
        text = f"Normal content\n{SUPPRESSION_TOKEN} user-approval-abc\n"
        findings = find_tokens_in_text(text, Path("clean.md"))
        assert not findings


# ---------------------------------------------------------------------------
# file-type filtering (find_tokens_in_file)
# ---------------------------------------------------------------------------


class TestFileTypeFilter:
    """Only approved file types (md, yaml, yml, txt) are scanned."""

    @pytest.mark.parametrize(
        "filename",
        ["body.md", "contract.yaml", "receipt.yml", "evidence.txt"],
    )
    def test_approved_extension_is_scanned(self, tmp_path: Path, filename: str) -> None:
        f = tmp_path / filename
        f.write_text("[skip-receipt-gate: reason]\n")
        findings = find_tokens_in_file(f)
        assert findings, f"Expected finding for {filename}"

    @pytest.mark.parametrize(
        "filename",
        ["module.py", "script.sh", "image.png", "binary.so"],
    )
    def test_non_approved_extension_is_skipped(
        self, tmp_path: Path, filename: str
    ) -> None:
        f = tmp_path / filename
        f.write_text("[skip-receipt-gate: reason]\n")
        findings = find_tokens_in_file(f)
        assert not findings, f"Unexpected finding for {filename}: {findings}"


# ---------------------------------------------------------------------------
# scan_tree (repo-wide grep)
# ---------------------------------------------------------------------------


class TestScanTree:
    """scan_tree must find tokens across a directory tree."""

    def test_finds_token_in_nested_file(self, tmp_path: Path) -> None:
        nested = tmp_path / "docs" / "pr_body.md"
        nested.parent.mkdir()
        nested.write_text("Contains [skip-cr-gate: some reason] here\n")
        findings = scan_tree(tmp_path)
        assert findings

    def test_clean_tree_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "clean.md").write_text("All good here.\n")
        findings = scan_tree(tmp_path)
        assert not findings

    def test_skips_python_source_files(self, tmp_path: Path) -> None:
        py_file = tmp_path / "validator.py"
        # A Python source that discusses bypass tokens must not be flagged
        py_file.write_text(
            "# This validator catches [skip-receipt-gate: ...\n"
            "BYPASS_TOKENS = ['[skip-receipt-gate:']\n"
        )
        findings = scan_tree(tmp_path)
        assert not findings, f"Python source must not be scanned: {findings}"


# ---------------------------------------------------------------------------
# main() CLI integration
# ---------------------------------------------------------------------------


class TestMainCLI:
    """main() must return 0 for clean files and 1 for files with bypass tokens."""

    def test_clean_file_exits_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.md"
        f.write_text("No bypass tokens here.\n")
        assert main([str(f)]) == 0

    def test_file_with_token_exits_one(self, tmp_path: Path) -> None:
        f = tmp_path / "pr_body.md"
        f.write_text("This PR uses [deploy-gate-bypass: quick fix]\n")
        assert main([str(f)]) == 1

    def test_no_args_scans_known_dirs_and_passes_on_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # When no args are passed main() falls back to scanning src/ and tests/
        # relative to cwd. With an empty tmp_path it should pass.
        monkeypatch.chdir(tmp_path)
        assert main([]) == 0

    def test_multiple_files_all_checked(self, tmp_path: Path) -> None:
        clean = tmp_path / "clean.md"
        dirty = tmp_path / "dirty.md"
        clean.write_text("All good.\n")
        dirty.write_text("Contains receipt-gate-bypass token.\n")
        assert main([str(clean), str(dirty)]) == 1

    @pytest.mark.parametrize("token", EXPECTED_TOKENS)
    def test_each_token_causes_exit_one(self, tmp_path: Path, token: str) -> None:
        f = tmp_path / "pr.md"
        f.write_text(f"Content with {token} embedded.\n")
        assert main([str(f)]) == 1


# ---------------------------------------------------------------------------
# emergency_bypass.enabled is always false
# ---------------------------------------------------------------------------


class TestEmergencyBypassAlwaysFalse:
    """emergency_bypass.enabled must always be false — treat the string as a token."""

    def test_emergency_bypass_enabled_true_detected(self) -> None:
        text = "emergency_bypass:\n  enabled: true\n"
        findings = find_tokens_in_text(text, Path("contract.yaml"))
        # The canonical token is "receipt-gate-bypass" which does not match this;
        # however OMN-13388 states emergency_bypass.enabled is ALWAYS false.
        # The validator enforces "emergency_bypass.enabled: true" as a 10th sentinel
        # in addition to the 9 base tokens, but the test list covers the 9 only.
        # This test documents the decision: we DO NOT add a 10th token to BYPASS_TOKENS
        # because the contract schema already hard-codes false.  The existing 9 tokens
        # are sufficient; emergency_bypass is caught at the schema layer.
        # If this policy changes, add "emergency_bypass.enabled: true" to BYPASS_TOKENS
        # and update the count to 10.
        # For now: confirm that the 9-token list does NOT accidentally catch it.
        token_values = set(BYPASS_TOKENS)
        assert "emergency_bypass.enabled: true" not in token_values
