# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Reproduce the OMN-14342 premise-check number from merged dev-PR history.

Replays the LIVE change-aware selector (``compute_selection``, forced
``feature_flag_enabled=True``) over a set of merged dev PRs and reports what
fraction would escalate to the full suite and which ``shared_module`` dominates.
This is the evidence that justified building the shadow instrumentation.

Reproduce end-to-end::

    gh pr list --repo OmniNode-ai/omnibase_core --base dev --state merged \
        --limit 120 --json number,headRefName,mergedAt,files > dev_prs.json
    uv run python -m scripts.ci.shadow_premise_replay --prs-json dev_prs.json

The 2026-07-10 baseline (120 merged omnibase_core dev PRs): 67-72% escalate to
the full suite; ``shared_module`` dominates (44-63% of all PRs); ``models`` is the
single dominant trigger (~29% of all PRs, ~2.2x the next module). The range is
pyproject.toml fail-closed (worst case) vs metadata-only (best case).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

from scripts.ci.detect_test_paths import SRC_PREFIX, compute_selection
from scripts.ci.test_selection_loader import load_adjacency_map

_ADJ_DEFAULT = Path(__file__).parent / "test_selection_adjacency.yaml"


def replay(prs: list[dict], adjacency_path: Path, *, pyproject_escalates: bool) -> dict:
    """Replay the selector over PR change sets.

    ``pyproject_escalates`` bounds the pyproject.toml effect: True = fail-closed
    (worst case, matches CI when the base cannot be read); False = treat every
    pyproject change as metadata-only (best case). The real number lies between.
    """
    config = load_adjacency_map(adjacency_path)
    shared = set(config.shared_modules)
    reason_hist: Counter[str] = Counter()
    shared_module_hist: Counter[str] = Counter()
    narrowed_paths: list[int] = []
    full = 0
    n = 0
    for pr in prs:
        files = [f["path"] for f in pr.get("files", [])]
        if not files:
            continue
        n += 1
        pyproj = None if ("pyproject.toml" in files and pyproject_escalates) else False
        sel = compute_selection(
            changed_files=files,
            adjacency_path=adjacency_path,
            ref_name=pr.get("headRefName", "feature-branch"),
            event_name="pull_request",
            feature_flag_enabled=True,
            pyproject_dependency_relevant=pyproj,
        )
        if sel.is_full_suite:
            full += 1
            assert sel.full_suite_reason is not None
            reason_hist[sel.full_suite_reason.value] += 1
            if sel.full_suite_reason.value == "shared_module":
                changed_modules = {
                    p[len(SRC_PREFIX) :].split("/", 1)[0]
                    for p in files
                    if p.startswith(SRC_PREFIX)
                } & set(config.adjacency.keys())
                for m in sorted(changed_modules & shared):
                    shared_module_hist[m] += 1
        else:
            narrowed_paths.append(len(sel.selected_paths))
    return {
        "n": n,
        "full": full,
        "narrowed": n - full,
        "reason_hist": dict(reason_hist.most_common()),
        "shared_module_hist": dict(shared_module_hist.most_common()),
        "narrowed_median_paths": (
            statistics.median(narrowed_paths) if narrowed_paths else 0
        ),
    }


def _print_report(label: str, r: dict) -> None:
    n = r["n"] or 1
    lines = [
        f"\n=== {label}: {r['n']} PRs ===",
        f"  full-suite escalated : {r['full']}/{r['n']} ({100 * r['full'] / n:.0f}%)",
        f"  narrowed (smart)     : {r['narrowed']}/{r['n']} "
        f"({100 * r['narrowed'] / n:.0f}%), median selected_paths="
        f"{r['narrowed_median_paths']:.0f}",
        "  reason histogram:",
    ]
    lines += [
        f"    {count:3} ({100 * count / n:2.0f}%) {reason}"
        for reason, count in r["reason_hist"].items()
    ]
    if r["shared_module_hist"]:
        lines.append("  which shared_module triggered SHARED_MODULE:")
        lines += [
            f"    {count:3}  {module}"
            for module, count in r["shared_module_hist"].items()
        ]
    sys.stdout.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce the OMN-14342 premise check"
    )
    parser.add_argument("--prs-json", type=Path, required=True)
    parser.add_argument("--adjacency", type=Path, default=_ADJ_DEFAULT)
    args = parser.parse_args(argv)

    prs = json.loads(args.prs_json.read_text(encoding="utf-8"))
    _print_report(
        "WORST CASE (pyproject fail-closed)",
        replay(prs, args.adjacency, pyproject_escalates=True),
    )
    _print_report(
        "BEST CASE (pyproject metadata-only)",
        replay(prs, args.adjacency, pyproject_escalates=False),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
