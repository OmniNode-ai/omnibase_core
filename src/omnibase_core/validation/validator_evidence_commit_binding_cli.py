# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI entrypoint for the Evidence-Commit binding validator (OMN-15111).

Wired into the shared ``receipt-gate.yml`` reusable workflow as a new step in
the existing, already-required ``receipt-gate / verify`` job — this is an
additive check inside that job, not a new required status-check context.

    uv run python -m omnibase_core.validation.validator_evidence_commit_binding_cli \\
        --pr-body-file /tmp/pr_body.txt \\
        --occ-sha-file /tmp/occ_sha.txt

``--occ-sha-file`` is the file receipt-gate.yml's "Resolve Evidence-Source"
step already writes (the resolved OCC commit-ish, or the literal string
``PENDING_MERGE`` when no Evidence-Source was required/resolved).

Exit codes:
    0 — no Evidence-Commit trailer, or trailer present and correctly bound
    1 — Evidence-Commit trailer present and invalid (malformed, dangling,
        unresolvable, or unbound to the resolved Evidence-Source)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from omnibase_core.validation.validator_evidence_commit_binding import (
    validate_evidence_commit_binding,
)

_DEFAULT_OCC_REPO = "OmniNode-ai/onex_change_control"


def _gh_commit_exists(repo: str, sha: str) -> bool:
    """True iff ``sha`` resolves to a real commit in ``repo`` via the GitHub API."""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/commits/{sha}", "--jq", ".sha"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip().lower() == sha.lower()


def _gh_is_ancestor_or_equal(repo: str, candidate: str, ref: str) -> bool:
    """True iff ``candidate`` is identical to, or a git-ancestor of, ``ref`` in ``repo``.

    Uses the GitHub compare API (``compare/{ref}...{candidate}``): a
    ``status`` of ``identical`` or ``behind`` means ``candidate`` is reachable
    from ``ref`` (i.e. an ancestor or the same commit) — the same convention
    receipt-gate.yml's "Resolve Evidence-Source" step already uses to
    validate a raw-SHA Evidence-Source against OCC main.
    """
    if candidate.lower() == ref.lower():
        return True
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/compare/{ref}...{candidate}", "--jq", ".status"],
        capture_output=True,
        text=True,
        check=False,
    )
    status = result.stdout.strip()
    return result.returncode == 0 and status in {"identical", "behind"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Evidence-Commit PR-body trailer's binding (OMN-15111)."
    )
    parser.add_argument(
        "--pr-body-file",
        required=True,
        help="Path to a file containing the PR body text.",
    )
    parser.add_argument(
        "--occ-sha-file",
        required=True,
        help=(
            "Path to a file containing the resolved Evidence-Source OCC SHA "
            "(or the literal string PENDING_MERGE / an empty/missing file when none was resolved)."
        ),
    )
    parser.add_argument("--occ-repo", default=_DEFAULT_OCC_REPO)
    args = parser.parse_args(argv)

    pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")
    occ_sha_path = Path(args.occ_sha_file)
    occ_sha_raw = (
        occ_sha_path.read_text(encoding="utf-8").strip()
        if occ_sha_path.exists()
        else ""
    )
    occ_sha = occ_sha_raw or None

    result = validate_evidence_commit_binding(
        pr_body,
        occ_sha,
        commit_exists=lambda sha: _gh_commit_exists(args.occ_repo, sha),
        is_ancestor_or_equal=lambda candidate, ref: _gh_is_ancestor_or_equal(
            args.occ_repo, candidate, ref
        ),
    )

    if result.ok:
        print(f"EVIDENCE-COMMIT OK: {result.message}")
        return 0

    print(
        f"::error::RECEIPT GATE FAILED (OMN-15111): {result.message}", file=sys.stderr
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
