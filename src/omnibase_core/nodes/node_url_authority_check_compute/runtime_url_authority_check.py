# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for the url-authority ratchet gate (OMN-12818, OMN-21520).

Staged-files mode (pre-commit)::

    python -m omnibase_core.nodes.node_url_authority_check_compute.runtime_url_authority_check file1.py ...

Full-repo scan (CI)::

    python -m omnibase_core.nodes.node_url_authority_check_compute.runtime_url_authority_check --all \\
        --repo omnibase_core --repo-root .

Seed / update baseline::

    python -m omnibase_core.nodes.node_url_authority_check_compute.runtime_url_authority_check \\
        --seed --repo omnibase_core --repo-root .
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.text_file_write.model_text_file_write_input import (
    ModelTextFileWriteInput,
)
from omnibase_core.models.nodes.url_authority_check.model_url_authority_check_input import (
    ModelUrlAuthorityCheckInput,
)
from omnibase_core.nodes.node_text_file_write_effect.handler import (
    NodeTextFileWriteEffect,
)
from omnibase_core.nodes.node_url_authority_check_compute.handler import (
    NodeUrlAuthorityCheckCompute,
)
from omnibase_core.validation.validator_url_authority import (
    _DEFAULT_BASELINE,
    _WIDENING_BASELINE_NAME,
    SUPPRESS_ANNOTATION,
    _is_msk_scannable,
    assert_baseline_shrinks_only,
    load_baseline,
    load_effective_baseline,
    partition_against_baseline,
    scan_tree,
)


def _err(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _out(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _update_baseline(
    repo: str, repo_root: Path, baseline_path: Path, *, seed: bool
) -> int:
    """Regenerate this repo's baseline subset (burn-down only)."""
    prior_entries: list[dict[str, str]] = []
    if baseline_path.exists():
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        all_entries = data.get("violations", []) if isinstance(data, dict) else []
        prior_entries = [
            e for e in all_entries if isinstance(e, dict) and "fingerprint" in e
        ]
    repo_before = {e["fingerprint"] for e in prior_entries if e.get("repo") == repo}
    other_entries = [e for e in prior_entries if e.get("repo") != repo]

    # Debt recorded in the widening seed stays there; it never migrates into
    # the primary baseline (which would read as growth).
    widening = load_baseline(baseline_path.parent / _WIDENING_BASELINE_NAME)
    fresh_violations = [
        v for v in scan_tree(repo, repo_root) if v.fingerprint not in widening
    ]
    fresh: list[dict[str, str]] = [
        {
            "repo": v.repo,
            "path": v.path,
            "rule": v.rule,
            "fingerprint": v.fingerprint,
        }
        for v in fresh_violations
    ]
    repo_after = {e["fingerprint"] for e in fresh}

    if not seed:
        try:
            assert_baseline_shrinks_only(repo_before, repo_after)
        except ValueError as exc:
            _err(f"URL-AUTHORITY BASELINE REJECTED: {exc}")
            return 1

    merged = sorted(
        [*other_entries, *fresh],
        key=lambda e: (e["repo"], e["path"], e["fingerprint"]),
    )
    NodeTextFileWriteEffect().handle(
        ModelTextFileWriteInput(
            path=str(baseline_path),
            text=json.dumps(
                {"schema_version": "1.0.0", "count": len(merged), "violations": merged},
                indent=2,
            )
            + "\n",
        )
    )
    action = "seeded" if seed else f"burned down {len(repo_before) - len(repo_after)}"
    _out(
        f"URL-AUTHORITY BASELINE updated for {repo}: {len(repo_after)} violation(s) "
        f"({action}). Total across repos: {len(merged)}."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Staged-files mode (pre-commit): pass file paths as positional args.
    Full-repo mode (CI): pass ``--all --repo <name> --repo-root <path>``.
    Baseline update: pass ``--seed`` or ``--update-baseline``.

    Exit codes:
        0 — no new violations (or grandfathered-only)
        1 — new violation(s) found or baseline grew
    """
    parser = argparse.ArgumentParser(
        prog="check-url-authority",
        description="url-authority ratchet gate (OMN-12818).",
    )
    parser.add_argument(
        "paths", nargs="*", help="Explicit files to scan (staged set, pre-commit mode)."
    )
    parser.add_argument(
        "--repo", default="omnibase_core", help="Repo name for fingerprints."
    )
    parser.add_argument(
        "--repo-root", default=".", help="Repo root for repo-relative paths."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Full-repo scan (CI mode) instead of explicit staged files.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Regenerate this repo's baseline subset (burn-down only).",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="One-time initialization of this repo's baseline subset (no shrink check).",
    )
    parser.add_argument(
        "--baseline",
        default=str(_DEFAULT_BASELINE),
        help="Path to the baseline JSON.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    baseline_path = Path(args.baseline)

    if args.update_baseline or args.seed:
        return _update_baseline(args.repo, repo_root, baseline_path, seed=args.seed)

    if args.all:
        violations = scan_tree(args.repo, repo_root)
    else:
        if not args.paths:
            _out("URL-AUTHORITY GATE: no files to scan.")
            return 0
        staged: list[ModelSourceFile] = []
        for raw in args.paths:
            p = Path(raw)
            if not p.is_file() or not _is_msk_scannable(p):
                continue
            try:
                source = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            try:
                rel = str(p.resolve().relative_to(repo_root.resolve()))
            except ValueError:
                rel = str(p)
            staged.append(ModelSourceFile(path=rel, source=source))
        violations = list(
            NodeUrlAuthorityCheckCompute()
            .handle(ModelUrlAuthorityCheckInput(repo=args.repo, files=tuple(staged)))
            .violations
        )

    baseline = load_effective_baseline(baseline_path)
    new, grandfathered = partition_against_baseline(violations, baseline)

    if new:
        _err(
            f"URL-AUTHORITY GATE FAILED: {len(new)} NEW violation(s) — every URL must "
            "resolve from a contract (routing authority / integration catalog), not a "
            "literal or a *_URL/*_DSN/*_ENDPOINT env read.\n"
        )
        for v in new:
            _err(f"  [{v.rule}] {v.repo}/{v.path}:{v.line}")
            _err(f"    {v.snippet}")
            _err(
                "    -> migrate to the resolver, or annotate "
                f"{SUPPRESS_ANNOTATION} <reason>"
            )
        return 1

    _out(
        f"URL-AUTHORITY GATE PASSED: 0 new violations "
        f"({len(grandfathered)} grandfathered)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
