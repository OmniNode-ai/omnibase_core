# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Evidence-Commit trailer binding validator (OMN-15111).

The receipt gate (``validator_receipt_gate.py``) resolves and validates the
canonical ``Evidence-Source: OCC#<n>`` / ``Evidence-Source: <sha>`` PR-body
trailer (OMN-10419). It does **not** validate the sibling, informal
``Evidence-Commit: <sha>`` trailer that has been hand-typed and
tool-generated into PR bodies fleet-wide since OMN-14494. Nothing resolves
that SHA against any repository — it is decorative text that looks
authoritative to a human reviewer but is checked by no gate.

Convention (confirmed empirically against ~50 recent product-repo PRs,
2026-07-25): ``Evidence-Commit`` cites the **onex_change_control (OCC)**
commit the adjacent ``Evidence-Source`` line resolves to — a cross-repo
citation, not a same-repo one. This module enforces that binding:

    1. No ``Evidence-Commit`` trailer -> PASS (not newly mandatory).
    2. Malformed (not a 7-40 char hex SHA) -> FAIL.
    3. No resolvable ``Evidence-Source`` to bind against -> FAIL (dangling
       citation).
    4. The cited SHA must exist as a real commit in onex_change_control,
       and must be identical to, or a git-ancestor of, the resolved
       Evidence-Source SHA -> otherwise FAIL.

The actual GitHub API resolution (does the commit exist? is it an ancestor?)
is injected via callables so this module is unit-testable without network
access. ``validator_evidence_commit_binding_cli.py`` supplies the real
``gh api``-backed resolvers for CI use.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

# Matches the first canonical "Evidence-Commit: <value>" line (column 0,
# trimmed). Deliberately mirrors the shape of validator_receipt_gate.py's
# Evidence-Source extraction (OMN-14682): a real stamp is column-0, one
# space after the colon, nothing else on the line.
_EVIDENCE_COMMIT_RE = re.compile(r"^Evidence-Commit:[ \t]*(\S+)[ \t]*$", re.MULTILINE)

# A well-formed git commit-ish: 7-40 lowercase/uppercase hex characters.
_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")

# Sentinel written by receipt-gate.yml's "Resolve Evidence-Source" step when
# a PR predates the OMN-10419 cutoff and has no Evidence-Source of its own.
_PENDING_MERGE_SENTINEL = "PENDING_MERGE"


@dataclass(frozen=True)
class ModelEvidenceCommitBindingResult:
    """Outcome of validating a PR body's Evidence-Commit trailer."""

    ok: bool
    message: str
    evidence_commit: str | None = None


def parse_evidence_commit(pr_body: str) -> str | None:
    """Return the trimmed value of the first canonical Evidence-Commit line, or None."""
    match = _EVIDENCE_COMMIT_RE.search(pr_body)
    if match is None:
        return None
    return match.group(1).strip()


def validate_evidence_commit_binding(
    pr_body: str,
    occ_sha: str | None,
    *,
    commit_exists: Callable[[str], bool],
    is_ancestor_or_equal: Callable[[str, str], bool],
) -> ModelEvidenceCommitBindingResult:
    """Validate the PR body's Evidence-Commit trailer against a resolved OCC SHA.

    Args:
        pr_body: Full PR description text.
        occ_sha: The Evidence-Source SHA already resolved by
            ``validator_receipt_gate.py`` / the CI "Resolve Evidence-Source"
            step, or ``None`` / ``"PENDING_MERGE"`` when no Evidence-Source
            was resolved for this PR.
        commit_exists: Returns True iff the given SHA is a real commit in
            onex_change_control.
        is_ancestor_or_equal: Returns True iff the first SHA is identical to,
            or a git-ancestor of, the second SHA in onex_change_control.

    Returns:
        A ``ModelEvidenceCommitBindingResult``. ``ok=True`` covers both "no
        trailer present" (nothing to validate) and "trailer present and
        correctly bound".
    """
    evidence_commit = parse_evidence_commit(pr_body)
    if evidence_commit is None:
        return ModelEvidenceCommitBindingResult(
            ok=True,
            message="No Evidence-Commit trailer present — nothing to validate.",
        )

    if not _SHA_RE.match(evidence_commit):
        return ModelEvidenceCommitBindingResult(
            ok=False,
            message=(
                f"Evidence-Commit value '{evidence_commit}' is not a well-formed "
                "7-40 character hex SHA."
            ),
            evidence_commit=evidence_commit,
        )

    if not occ_sha or occ_sha == _PENDING_MERGE_SENTINEL:
        return ModelEvidenceCommitBindingResult(
            ok=False,
            message=(
                f"Evidence-Commit '{evidence_commit}' is present but there is no "
                "resolvable Evidence-Source line to bind it to (dangling citation)."
            ),
            evidence_commit=evidence_commit,
        )

    if not commit_exists(evidence_commit):
        return ModelEvidenceCommitBindingResult(
            ok=False,
            message=(
                f"Evidence-Commit SHA '{evidence_commit}' does not resolve to a "
                "real commit in onex_change_control. Fabricated, truncated, or "
                "wrong-repo SHA."
            ),
            evidence_commit=evidence_commit,
        )

    if evidence_commit == occ_sha or is_ancestor_or_equal(evidence_commit, occ_sha):
        return ModelEvidenceCommitBindingResult(
            ok=True,
            message=(
                f"Evidence-Commit '{evidence_commit}' is bound to the resolved "
                f"Evidence-Source '{occ_sha}'."
            ),
            evidence_commit=evidence_commit,
        )

    return ModelEvidenceCommitBindingResult(
        ok=False,
        message=(
            f"Evidence-Commit '{evidence_commit}' does not bind to the resolved "
            f"Evidence-Source '{occ_sha}' — it is neither identical nor a "
            "git-ancestor of it."
        ),
        evidence_commit=evidence_commit,
    )
