# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the Evidence-Commit trailer binding validator (OMN-15111).

Found live 2026-07-25: the PR-body ``Evidence-Commit:`` trailer (in use
fleet-wide since OMN-14494, ~1045 product-repo merged PRs carry it) is never
validated by any gate — no CI job, no OCC receipt, no pre-commit hook ever
resolves the cited SHA. These tests pin the fail-closed contract this module
must enforce: a fabricated/unbound SHA fails; a real, correctly-bound SHA
passes.
"""

from __future__ import annotations

from omnibase_core.validation.validator_evidence_commit_binding import (
    ModelEvidenceCommitBindingResult,
    parse_evidence_commit,
    validate_evidence_commit_binding,
)

_REAL_OCC_SHA = "53e14f927a6ef80910fabeeabe58576b4cb21087"  # pragma: allowlist secret
_ANCESTOR_SHA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # pragma: allowlist secret
_FABRICATED_SHA = "21b42c7879748f459cb108d009071a352c1b91dc"  # pragma: allowlist secret


def _always_exists(sha: str) -> bool:
    return True


def _never_exists(sha: str) -> bool:
    return False


def _no_ancestry(candidate: str, ref: str) -> bool:
    return False


def _ancestor_of_ref(candidate: str, ref: str) -> bool:
    return candidate == _ANCESTOR_SHA and ref == _REAL_OCC_SHA


class TestParseEvidenceCommit:
    def test_absent_returns_none(self) -> None:
        assert parse_evidence_commit("Closes OMN-1\n\nNo trailer here.\n") is None

    def test_present_returns_trimmed_value(self) -> None:
        body = f"Closes OMN-1\n\nEvidence-Commit: {_REAL_OCC_SHA}\n"
        assert parse_evidence_commit(body) == _REAL_OCC_SHA

    def test_only_inside_fenced_code_block_is_still_matched_at_column_zero(
        self,
    ) -> None:
        # This module deliberately only anchors on column-0 MULTILINE match,
        # matching the parse layer's job. Fence-awareness is out of scope
        # here (mirrors validator_receipt_gate.py's stricter Evidence-Source
        # shape check, which is a separate, already-existing concern).
        body = f"```\nEvidence-Commit: {_REAL_OCC_SHA}\n```\n"
        assert parse_evidence_commit(body) == _REAL_OCC_SHA


class TestValidateEvidenceCommitBinding:
    def test_no_trailer_passes(self) -> None:
        result = validate_evidence_commit_binding(
            "Closes OMN-1\n\nEvidence-Source: OCC#1234\n",
            occ_sha=_REAL_OCC_SHA,
            commit_exists=_never_exists,
            is_ancestor_or_equal=_no_ancestry,
        )
        assert result.ok is True
        assert isinstance(result, ModelEvidenceCommitBindingResult)

    def test_malformed_sha_fails(self) -> None:
        body = "Closes OMN-1\n\nEvidence-Commit: not-a-sha!!\n"
        result = validate_evidence_commit_binding(
            body,
            occ_sha=_REAL_OCC_SHA,
            commit_exists=_always_exists,
            is_ancestor_or_equal=_no_ancestry,
        )
        assert result.ok is False
        assert "not a well-formed" in result.message

    def test_dangling_citation_with_no_evidence_source_fails(self) -> None:
        body = f"Closes OMN-1\n\nEvidence-Commit: {_REAL_OCC_SHA}\n"
        result = validate_evidence_commit_binding(
            body,
            occ_sha=None,
            commit_exists=_always_exists,
            is_ancestor_or_equal=_no_ancestry,
        )
        assert result.ok is False
        assert "dangling citation" in result.message

    def test_pending_merge_sentinel_treated_as_no_evidence_source(self) -> None:
        body = f"Closes OMN-1\n\nEvidence-Commit: {_REAL_OCC_SHA}\n"
        result = validate_evidence_commit_binding(
            body,
            occ_sha="PENDING_MERGE",
            commit_exists=_always_exists,
            is_ancestor_or_equal=_no_ancestry,
        )
        assert result.ok is False

    def test_fabricated_sha_that_does_not_resolve_fails(self) -> None:
        # This is the seeded violation: a well-formed-looking hex SHA that
        # simply does not exist in onex_change_control (commit_exists=False).
        body = f"Closes OMN-1\n\nEvidence-Source: OCC#4794\nEvidence-Commit: {_FABRICATED_SHA}\n"
        result = validate_evidence_commit_binding(
            body,
            occ_sha=_REAL_OCC_SHA,
            commit_exists=_never_exists,
            is_ancestor_or_equal=_no_ancestry,
        )
        assert result.ok is False
        assert "does not resolve to a real commit" in result.message

    def test_exact_match_to_resolved_evidence_source_passes(self) -> None:
        body = f"Closes OMN-1\n\nEvidence-Source: OCC#4800\nEvidence-Commit: {_REAL_OCC_SHA}\n"
        result = validate_evidence_commit_binding(
            body,
            occ_sha=_REAL_OCC_SHA,
            commit_exists=_always_exists,
            is_ancestor_or_equal=_no_ancestry,
        )
        assert result.ok is True
        assert "is bound to" in result.message

    def test_ancestor_of_resolved_evidence_source_passes(self) -> None:
        body = f"Closes OMN-1\n\nEvidence-Source: OCC#4786\nEvidence-Commit: {_ANCESTOR_SHA}\n"
        result = validate_evidence_commit_binding(
            body,
            occ_sha=_REAL_OCC_SHA,
            commit_exists=_always_exists,
            is_ancestor_or_equal=_ancestor_of_ref,
        )
        assert result.ok is True

    def test_unrelated_real_commit_not_bound_to_evidence_source_fails(self) -> None:
        # The critical negative case: the SHA is a REAL commit somewhere in
        # onex_change_control (commit_exists=True) but is unrelated to the
        # PR's actual Evidence-Source binding (not identical, not an
        # ancestor) — e.g. copy-pasted from a different ticket's receipt.
        body = f"Closes OMN-1\n\nEvidence-Source: OCC#4794\nEvidence-Commit: {_ANCESTOR_SHA}\n"
        result = validate_evidence_commit_binding(
            body,
            occ_sha=_REAL_OCC_SHA,
            commit_exists=_always_exists,
            is_ancestor_or_equal=_no_ancestry,
        )
        assert result.ok is False
        assert "does not bind to the resolved Evidence-Source" in result.message
