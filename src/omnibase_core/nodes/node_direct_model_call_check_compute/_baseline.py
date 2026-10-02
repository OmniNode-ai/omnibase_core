# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The shrink-only baseline: matching, growth, tickets and rendering (OMN-20295).

Pure: the EFFECT node reads and writes the file; everything here only compares
and renders entries.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import date
from typing import Final

import yaml

from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_baseline_entry import (
    ModelDirectModelCallBaselineEntry,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_comparison import (
    ModelDirectModelCallComparison,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_finding import (
    ModelDirectModelCallFinding,
)
from omnibase_core.models.nodes.direct_model_call_check.model_direct_model_call_policy import (
    ModelDirectModelCallPolicy,
)

__all__ = [
    "added_entries",
    "bootstrap_entries",
    "compare_with_baseline",
    "entry_problems",
    "render_baseline",
    "shrink_entries",
]

_BASELINE_HEADER: Final[str] = """\
# Baseline for check-direct-model-call (OMN-20295).
# A model call must sit inside a sanctioned delegation
# node package (omnibase_core nodes/node_direct_model_call_check_compute/policy.yaml).
#
# RULE: entries only leave. A site not listed here fails. An entry that no
# longer matches a site fails until it is removed. An entry past its expiry no
# longer covers its site. CI and the pre-commit hook refuse a change whose copy
# of this file carries an entry, a later expiry or another ticket that its
# base did not. Crush sites name OMN-20290 for their removal.
#
# Regenerate only to SHRINK it:
#   python -m omnibase_core.nodes.node_direct_model_call_check_effect.runtime_direct_model_call \\
#     --repo <repo> --baseline <this file> --write-baseline
"""


def entry_problems(
    policy: ModelDirectModelCallPolicy,
    entries: Sequence[ModelDirectModelCallBaselineEntry],
) -> list[str]:
    """Entries that name the wrong removal ticket for their target."""
    problems: list[str] = []
    for entry in entries:
        required = policy.required_ticket_by_target.get(entry.target)
        if required is not None and entry.ticket != required:
            problems.append(
                f"{entry.path}: {entry.kind} {entry.target} in {entry.symbol} must name "
                f"{required} for its removal, not {entry.ticket}"
            )
    return problems


def compare_with_baseline(
    findings: Sequence[ModelDirectModelCallFinding],
    baseline: Sequence[ModelDirectModelCallBaselineEntry],
    today: date,
) -> ModelDirectModelCallComparison:
    """Match findings to baseline entries as a multiset keyed by site, not line."""
    live = Counter(e.key() for e in baseline if e.expires >= today)
    seen = Counter(f.key() for f in findings)
    new: list[ModelDirectModelCallFinding] = []
    used: Counter[tuple[str, str, str, str]] = Counter()
    for finding in findings:
        key = finding.key()
        if used[key] < live[key]:
            used[key] += 1
        else:
            new.append(finding)
    stale: list[ModelDirectModelCallBaselineEntry] = []
    budget = Counter(seen)
    for entry in sorted(baseline, key=lambda e: e.key()):
        if budget[entry.key()] > 0:
            budget[entry.key()] -= 1
        else:
            stale.append(entry)
    expired = [e for e in baseline if e.expires < today]
    return ModelDirectModelCallComparison(
        new=tuple(new), stale=tuple(stale), expired=tuple(expired)
    )


def added_entries(
    base: Sequence[ModelDirectModelCallBaselineEntry],
    head: Sequence[ModelDirectModelCallBaselineEntry],
) -> list[ModelDirectModelCallBaselineEntry]:
    """Entries of ``head`` that ``base`` did not carry, or carried with an
    earlier expiry or another ticket. Entries only leave; none is extended."""
    remaining = Counter((e.key(), e.ticket, e.expires) for e in base)
    grown: list[ModelDirectModelCallBaselineEntry] = []
    for entry in head:
        signature = (entry.key(), entry.ticket, entry.expires)
        if remaining[signature] > 0:
            remaining[signature] -= 1
        else:
            grown.append(entry)
    return grown


def shrink_entries(
    findings: Sequence[ModelDirectModelCallFinding],
    baseline: Sequence[ModelDirectModelCallBaselineEntry],
) -> tuple[list[ModelDirectModelCallBaselineEntry], list[ModelDirectModelCallFinding]]:
    """The entries that still match a site, and the sites none of them covers."""
    remaining = list(findings)
    kept: list[ModelDirectModelCallBaselineEntry] = []
    for entry in baseline:
        match = next((f for f in remaining if f.key() == entry.key()), None)
        if match is not None:
            remaining.remove(match)
            kept.append(entry)
    return kept, remaining


def bootstrap_entries(
    policy: ModelDirectModelCallPolicy,
    findings: Sequence[ModelDirectModelCallFinding],
    rules: Sequence[tuple[str, str]],
    expires: date,
) -> tuple[list[ModelDirectModelCallBaselineEntry], list[ModelDirectModelCallFinding]]:
    """A first baseline: each site with its removal ticket, and the sites with none.

    A target with a required ticket (crush: OMN-20290) always names it; any
    other site takes the ticket of the first path-prefix rule it falls under
    (``*`` matches every path).
    """
    entries: list[ModelDirectModelCallBaselineEntry] = []
    unticketed: list[ModelDirectModelCallFinding] = []
    for finding in findings:
        ticket = policy.required_ticket_by_target.get(finding.target)
        if ticket is None:
            ticket = next(
                (
                    t
                    for prefix, t in rules
                    if prefix == "*" or finding.path.startswith(prefix)
                ),
                None,
            )
        if ticket is None:
            unticketed.append(finding)
            continue
        entries.append(
            ModelDirectModelCallBaselineEntry(
                path=finding.path,
                kind=finding.kind,
                symbol=finding.symbol,
                target=finding.target,
                ticket=ticket,
                expires=expires,
            )
        )
    return entries, unticketed


def render_baseline(entries: Sequence[ModelDirectModelCallBaselineEntry]) -> str:
    """The committed baseline document, sorted by site key."""
    lines = ["---", _BASELINE_HEADER, "schema_version: 1"]
    ordered = sorted(entries, key=lambda e: (*e.key(), e.ticket, e.expires))
    if not ordered:
        lines.append("entries: []")
    else:
        lines.append("entries:")
        for entry in ordered:
            fields = entry.model_dump(mode="json")
            for index, (name, value) in enumerate(fields.items()):
                scalar = yaml.safe_dump(value, default_flow_style=True, width=10_000)
                scalar = scalar.removesuffix("\n...\n").strip()
                prefix = "  - " if index == 0 else "    "
                lines.append(f"{prefix}{name}: {scalar}")
    return "\n".join(lines) + "\n"
