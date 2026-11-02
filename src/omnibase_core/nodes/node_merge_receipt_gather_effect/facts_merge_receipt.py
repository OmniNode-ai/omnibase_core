# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pure fact gathering for the merge-side receipt check (OMN-21926).

Turns the text of the PR watcher state and of the rolling ledger into the typed facts
the checker judges. It performs no I/O; names of check runs, surfaces and thresholds
come from the contract's rule rows, never from this module.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from omnibase_core.models.merge_receipt.model_merge_receipt_pr import (
    ModelMergeReceiptPr,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_record import (
    ModelMergeReceiptRecord,
)

__all__ = ["percentile", "slot_seconds", "watcher_facts"]

_LEDGER_TS = "%Y-%m-%dT%H:%M:%SZ"


def _passing_checks(ci: Mapping[str, Any]) -> list[str]:
    """Names of the check runs the watcher read on its sha that are neither red nor pending."""
    refused = set(ci.get("red") or ()) | set(ci.get("pending") or ())
    refused |= set(ci.get("cancelled") or ())
    return [
        str(entry[0])
        for entry in ci.get("detail") or ()
        if entry and str(entry[0]) not in refused
    ]


def watcher_facts(
    state: Mapping[str, Any],
    repos: Iterable[str],
    check_names: Iterable[str],
    paths_for: Callable[[str, int, str, str], tuple[str, ...] | None],
) -> tuple[tuple[ModelMergeReceiptPr, ...], tuple[str, ...]]:
    """Open pull requests of ``repos`` as facts, and the ``repo#n`` ids whose paths were unreadable.

    ``paths_for(repo, number, base, head_sha)`` returns the changed paths or ``None`` when
    they cannot be read; such a pull request is left out of the facts, never guessed at.
    """
    wanted = set(repos)
    names = set(check_names)
    facts: list[ModelMergeReceiptPr] = []
    unreadable: list[str] = []
    for key, entry in sorted(state.get("prs", {}).items()):
        info = entry.get("facts", {})
        repo = str(info.get("repo", ""))
        if repo not in wanted or info.get("state") != "OPEN":
            continue
        number = int(info["number"])
        head = str(info["head_sha"])
        paths = paths_for(repo, number, str(info.get("base", "")), head)
        if paths is None:
            unreadable.append(key)
            continue
        ci = entry.get("ci") or {}
        sha = str(ci.get("sha") or "")
        records = tuple(
            ModelMergeReceiptRecord(
                source=name,
                sha=sha,
                repo=repo,
                pr_number=number,
                branch=str(info.get("head_ref", "")),
            )
            for name in _passing_checks(ci)
            if name in names and sha
        )
        facts.append(
            ModelMergeReceiptPr(
                repo=repo,
                number=number,
                head_sha=head,
                head_ref=str(info.get("head_ref", "")),
                body=str(info.get("body", "")),
                changed_paths=paths,
                receipts=records,
            )
        )
    return tuple(facts), tuple(unreadable)


def _cells(row: str) -> dict[str, str]:
    cells: dict[str, str] = {}
    for cell in row.split(" | ")[2:]:
        key, sep, value = cell.partition("=")
        if sep and key.strip() not in cells:
            cells[key.strip()] = value.strip()
    return cells


def _seconds(start: str, end: str) -> float | None:
    from datetime import UTC, datetime

    try:
        return (
            datetime.strptime(end, _LEDGER_TS).replace(tzinfo=UTC)
            - datetime.strptime(start, _LEDGER_TS).replace(tzinfo=UTC)
        ).total_seconds()
    except ValueError:
        return None


def slot_seconds(ledger_rows: Iterable[str], surface_pattern: str) -> list[float]:
    """Seconds from each HOLD to the RELEASE whose ``re=`` names its ``id=``, on a matching surface."""
    surface = re.compile(surface_pattern)
    holds: dict[str, tuple[str, str]] = {}
    releases: list[tuple[str, str, str]] = []
    for row in ledger_rows:
        parts = row.split(" | ")
        if len(parts) < 3:
            continue
        kind = parts[1].strip()
        if kind not in ("HOLD", "RELEASE"):
            continue
        cells = _cells(row)
        if kind == "HOLD" and "id" in cells:
            holds[cells["id"]] = (parts[0].strip(), cells.get("surface", ""))
        elif kind == "RELEASE" and "re" in cells:
            releases.append((parts[0].strip(), cells["re"], cells.get("surface", "")))
    out: list[float] = []
    for released_at, hold_id, release_surface in releases:
        if hold_id not in holds:
            continue
        held_at, hold_surface = holds[hold_id]
        if not (surface.search(hold_surface) or surface.search(release_surface)):
            continue
        seconds = _seconds(held_at, released_at)
        if seconds is not None and seconds >= 0:
            out.append(seconds)
    return out


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile of a non-empty list."""
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]
