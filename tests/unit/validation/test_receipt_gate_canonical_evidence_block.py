# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-14682 — canonical Evidence-Source block + pre-push shape check.

The Receipt Gate's ``^Evidence-Source:`` MULTILINE extractor matched any
column-0 stamp-shaped line, including one quoted as an EXAMPLE inside a fenced
code block or blockquote (common in meta-PRs about the gate itself). That
false-positive either satisfied the gate on prose or, when a real stamp and an
example coexisted, false-blocked the PR with a "multiple Evidence-Source lines"
error that forced manual body normalization.

These tests pin BOTH directions so neither re-breaks (whack-a-mole):

* FALSE-POSITIVE (this ticket): a stamp that lives only in a fence/blockquote is
  NOT read as canonical; a real stamp coexisting with a fenced example is used
  on its own without a spurious multiple-lines block.
* FALSE-NEGATIVE (OMN-14410): a genuine disclaimer still skips identity binding;
  a malformed reference still hard-fails; a valid reference still binds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.validator_receipt_gate import (
    check_evidence_source_shape,
    classify_evidence_source_stamp,
    parse_evidence_source,
    strip_noncanonical_regions,
    validate_pr_receipts,
)

pytestmark = pytest.mark.unit


def _empty_dirs(tmp_path: Path) -> tuple[Path, Path]:
    contracts = tmp_path / "contracts"
    receipts = tmp_path / "receipts"
    contracts.mkdir()
    receipts.mkdir()
    return contracts, receipts


# ---------------------------------------------------------------------------
# strip_noncanonical_regions — the core primitive
# ---------------------------------------------------------------------------


class TestStripNoncanonicalRegions:
    def test_blanks_backtick_fenced_stamp(self) -> None:
        body = "Intro\n\n```\nEvidence-Source: OCC#1234\n```\n\nOutro"
        stripped = strip_noncanonical_regions(body)
        assert "Evidence-Source: OCC#1234" not in stripped
        assert "Intro" in stripped
        assert "Outro" in stripped

    def test_blanks_tilde_fenced_stamp(self) -> None:
        body = "~~~\nEvidence-Source: OCC#1234\n~~~"
        assert "Evidence-Source" not in strip_noncanonical_regions(body)

    def test_blanks_fence_with_info_string(self) -> None:
        body = "```text\nEvidence-Source: OCC#1234\n```"
        assert "Evidence-Source" not in strip_noncanonical_regions(body)

    def test_blanks_blockquote_stamp(self) -> None:
        body = "> Evidence-Source: OCC#1234"
        assert "Evidence-Source" not in strip_noncanonical_regions(body)

    def test_preserves_canonical_column0_stamp(self) -> None:
        body = "Evidence-Source: OCC#1234\nEvidence-Ticket: OMN-1"
        stripped = strip_noncanonical_regions(body)
        assert "Evidence-Source: OCC#1234" in stripped
        assert "Evidence-Ticket: OMN-1" in stripped

    def test_keeps_real_stamp_drops_fenced_example(self) -> None:
        body = (
            "Evidence-Source: OCC#500\n"
            "Evidence-Ticket: OMN-1\n\n"
            "For example:\n\n"
            "```\nEvidence-Source: OCC#999\n```\n"
        )
        stripped = strip_noncanonical_regions(body)
        assert "OCC#500" in stripped
        assert "OCC#999" not in stripped

    def test_unterminated_fence_fails_closed(self) -> None:
        # An opening fence with no close blanks everything after it.
        body = "```\nEvidence-Source: OCC#1234\nEvidence-Ticket: OMN-1"
        stripped = strip_noncanonical_regions(body)
        assert "Evidence-Source" not in stripped
        assert "Evidence-Ticket" not in stripped

    def test_idempotent(self) -> None:
        body = "A\n```\nEvidence-Source: OCC#1\n```\nB"
        once = strip_noncanonical_regions(body)
        twice = strip_noncanonical_regions(once)
        assert once == twice

    def test_no_fence_body_unchanged_by_line_content(self) -> None:
        body = "Evidence-Source: OCC#1\nEvidence-Ticket: OMN-1"
        assert strip_noncanonical_regions(body) == body


# ---------------------------------------------------------------------------
# FALSE-POSITIVE direction (OMN-14682): fenced/quoted stamp is not canonical
# ---------------------------------------------------------------------------


class TestFalsePositiveFencedStamp:
    def test_parse_evidence_source_ignores_fenced_stamp(self) -> None:
        body = "Closes OMN-1\n\n```\nEvidence-Source: OCC#1234\n```"
        assert parse_evidence_source(body) == (None, None)

    def test_parse_evidence_source_ignores_blockquoted_stamp(self) -> None:
        body = "Closes OMN-1\n\n> Evidence-Source: OCC#1234"
        assert parse_evidence_source(body) == (None, None)

    def test_parse_evidence_source_uses_real_stamp_over_fenced_example(self) -> None:
        body = (
            "Closes OMN-1\n\n"
            "Evidence-Source: OCC#500\n"
            "Evidence-Ticket: OMN-1\n\n"
            "```\nEvidence-Source: OCC#999\n```\n"
        )
        assert parse_evidence_source(body) == ("500", None)

    def test_classify_ignores_fenced_stamp(self) -> None:
        body = "```\nEvidence-Source: not-a-ref garbage\n```"
        attempted, _is_disclaimer, value = classify_evidence_source_stamp(body)
        assert attempted is False
        assert value is None

    def test_gate_does_not_report_multiple_lines_for_real_plus_fenced(
        self, tmp_path: Path
    ) -> None:
        # Real stamp + a fenced example must NOT trip the multiple-lines block.
        contracts, receipts = _empty_dirs(tmp_path)
        body = (
            "Closes OMN-1\n\n"
            "Evidence-Source: OCC#500\n"
            "Evidence-Ticket: OMN-1\n\n"
            "Documented format:\n\n"
            "```\nEvidence-Source: OCC#999\n```\n"
        )
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_title="OMN-1: something",
            branch_name="jonah/omn-1-x",
        )
        assert result.passed is False
        assert "multiple" not in result.message.lower()

    def test_gate_multiple_lines_still_fires_for_two_real_stamps(
        self, tmp_path: Path
    ) -> None:
        # Two genuine column-0 stamps remain ambiguous → fail closed.
        contracts, receipts = _empty_dirs(tmp_path)
        body = "Closes OMN-1\n\nEvidence-Source: OCC#500\nEvidence-Source: OCC#600\n"
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=contracts,
            receipts_dir=receipts,
        )
        assert result.passed is False
        assert "multiple Evidence-Source" in result.message

    def test_gate_fenced_only_stamp_is_treated_as_no_evidence(
        self, tmp_path: Path
    ) -> None:
        # AC1: prose/fenced-only mention (no structured block) fails the gate
        # (here: no receipt exists, and the fenced stamp is not counted).
        contracts, receipts = _empty_dirs(tmp_path)
        body = "Closes OMN-1\n\n```\nEvidence-Source: OCC#1234\n```\n"
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_title="OMN-1: something",
        )
        assert result.passed is False
        # It must NOT fail on identity binding (the fenced stamp did not trigger
        # it) — it fails on the missing contract/receipt for the cited ticket.
        assert "IDENTITY BINDING" not in result.message
        assert "no contract" in result.message.lower()


# ---------------------------------------------------------------------------
# FALSE-NEGATIVE direction (OMN-14410) stays fixed
# ---------------------------------------------------------------------------


class TestFalseNegativeDirectionPreserved:
    def test_disclaimer_still_classifies_as_disclaimer(self) -> None:
        attempted, is_disclaimer, _ = classify_evidence_source_stamp(
            "Evidence-Source: N/A"
        )
        assert attempted is True
        assert is_disclaimer is True

    def test_prose_disclaimer_still_skips_binding(self, tmp_path: Path) -> None:
        contracts, receipts = _empty_dirs(tmp_path)
        body = (
            "Closes OMN-1\n\n"
            "Evidence-Source: does not apply — this PR IS the evidence source\n"
        )
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_title="OMN-1: something",
        )
        # Skips identity binding; fails later on missing receipts, not on binding.
        assert result.passed is False
        assert "IDENTITY BINDING" not in result.message

    def test_malformed_reference_still_hard_fails(self, tmp_path: Path) -> None:
        contracts, receipts = _empty_dirs(tmp_path)
        body = "Closes OMN-1\n\nEvidence-Source: OCC#12 34 broken\n"
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_title="OMN-1: something",
        )
        assert result.passed is False
        assert "malformed" in result.message.lower()

    def test_valid_reference_still_requires_evidence_ticket(
        self, tmp_path: Path
    ) -> None:
        contracts, receipts = _empty_dirs(tmp_path)
        body = "Closes OMN-1\n\nEvidence-Source: OCC#1234\n"
        result = validate_pr_receipts(
            pr_body=body,
            contracts_dir=contracts,
            receipts_dir=receipts,
            pr_title="OMN-1: something",
        )
        assert result.passed is False
        assert "Evidence-Ticket" in result.message


# ---------------------------------------------------------------------------
# check_evidence_source_shape — the network-free pre-push primitive (AC3)
# ---------------------------------------------------------------------------


class TestCheckEvidenceSourceShape:
    def test_fenced_only_stamp_fails(self) -> None:
        body = "Closes OMN-1\n\n```\nEvidence-Source: OCC#1234\n```"
        result = check_evidence_source_shape(body)
        assert result.passed is False
        assert "only inside a fenced code block" in result.message

    def test_blockquoted_only_stamp_is_shape_clean(self) -> None:
        # A ``> Evidence-Source:`` line is not matched by the column-0 stamp
        # pattern at all, so it reads as "no stamp present" (shape-clean). The
        # real protection is that parse_evidence_source also ignores it, so the
        # receipt gate still fails closed on the missing genuine evidence.
        result = check_evidence_source_shape("> Evidence-Source: OCC#1234")
        assert result.passed is True
        assert parse_evidence_source("> Evidence-Source: OCC#1234") == (None, None)

    def test_multiple_canonical_stamps_fail(self) -> None:
        body = "Evidence-Source: OCC#1\nEvidence-Source: OCC#2"
        result = check_evidence_source_shape(body)
        assert result.passed is False
        assert "multiple canonical" in result.message

    def test_valid_reference_with_ticket_passes(self) -> None:
        body = "Evidence-Source: OCC#1234\nEvidence-Ticket: OMN-1"
        result = check_evidence_source_shape(body)
        assert result.passed is True

    def test_valid_reference_without_ticket_fails(self) -> None:
        result = check_evidence_source_shape("Evidence-Source: OCC#1234")
        assert result.passed is False
        assert "Evidence-Ticket" in result.message

    def test_malformed_reference_fails(self) -> None:
        result = check_evidence_source_shape("Evidence-Source: OCC#12 34 broken")
        assert result.passed is False
        assert "malformed" in result.message.lower()

    def test_recognized_disclaimer_passes(self) -> None:
        result = check_evidence_source_shape("Evidence-Source: N/A")
        assert result.passed is True

    def test_no_stamp_is_shape_clean(self) -> None:
        result = check_evidence_source_shape("Closes OMN-1\n\nNo stamp here.")
        assert result.passed is True

    def test_real_stamp_plus_fenced_example_passes(self) -> None:
        body = (
            "Evidence-Source: OCC#500\n"
            "Evidence-Ticket: OMN-1\n\n"
            "```\nEvidence-Source: OCC#999\n```\n"
        )
        result = check_evidence_source_shape(body)
        assert result.passed is True


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------


class TestEvidenceShapeCli:
    def test_cli_pass_valid_reference(self, capsys: pytest.CaptureFixture[str]) -> None:
        from omnibase_core.validation.validator_evidence_shape_cli import main

        rc = main(["--pr-body", "Evidence-Source: OCC#1234\nEvidence-Ticket: OMN-1"])
        assert rc == 0

    def test_cli_fail_fenced_only(self, capsys: pytest.CaptureFixture[str]) -> None:
        from omnibase_core.validation.validator_evidence_shape_cli import main

        rc = main(["--pr-body", "```\nEvidence-Source: OCC#1234\n```"])
        assert rc == 1

    def test_cli_reads_body_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from omnibase_core.validation.validator_evidence_shape_cli import main

        body_file = tmp_path / "body.txt"
        body_file.write_text(
            "Evidence-Source: OCC#1234\nEvidence-Ticket: OMN-1", encoding="utf-8"
        )
        rc = main(["--pr-body-file", str(body_file)])
        assert rc == 0

    def test_cli_usage_error_without_body(self) -> None:
        from omnibase_core.validation.validator_evidence_shape_cli import main

        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 2
