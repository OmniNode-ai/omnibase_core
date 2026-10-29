# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerFindingBaseline -- the one shrink-only baseline shared by source-finding hooks.

A baseline entry is ``(path, rule, normalized source text)``; the line number is not
part of it, so an edit above a finding never breaks its entry. Entries and findings
are counted as multisets: a second identical finding in a file is new, and a finding
that only moved still matches. A baselined finding passes; a finding outside the
baseline fails; an in-scope entry with no finding fails as stale, so the baseline is a
ratchet that cannot keep silent headroom. ``shrink`` never adds an entry.

Pure: no filesystem, no clock, no global state. Ticket: OMN-21433.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Final, Literal

import yaml

from omnibase_core.models.finding_baseline.model_finding_baseline import (
    ModelFindingBaseline,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_comparison import (
    ModelFindingBaselineComparison,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_entry import (
    ModelFindingBaselineEntry,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_input import (
    ModelFindingBaselineInput,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_scope import (
    ModelFindingBaselineScope,
)
from omnibase_core.models.finding_baseline.model_finding_baseline_shrink import (
    ModelFindingBaselineShrink,
)
from omnibase_core.models.finding_baseline.model_source_finding import (
    ModelSourceFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = ["HandlerFindingBaseline", "normalize_text"]

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"
_STALE_REMEDIATION: Final[str] = (
    "The finding is gone: run the hook with --write-baseline to shrink the baseline."
)
_HEADER: Final[str] = """\
# Shrink-only baseline for the {hook} hook (OMN-21433).
# One entry per tolerated finding: file path, rule id and the normalized offending
# source text (never a line number). Entries are counted: two identical findings in
# one file need two identical entries.
#
# RULE: entries only leave. A finding not listed here fails. An entry whose finding
# is gone fails until it is removed. --write-baseline creates this file when absent
# and afterwards only shrinks it; it refuses, with a nonzero exit, any write that
# would add an entry.
"""


def normalize_text(line: str) -> str:
    """Collapse whitespace so reindenting a finding does not break its entry."""
    return " ".join(line.split())


class HandlerFindingBaseline:
    """COMPUTE handler: compares findings with a baseline and shrinks it."""

    def handle(self, request: ModelFindingBaselineInput) -> ModelValidationReport:
        """Typed request in, typed report out: every new finding and stale entry is a FAIL."""
        baseline = request.baseline
        comparison = self.compare(
            request.findings,
            baseline.entries if baseline is not None else (),
            request.scope,
        )
        embeds: list[ModelValidationFindingEmbed] = []
        for finding in (*comparison.unbaselinable, *comparison.new):
            location = f"{finding.path}:{finding.line}"
            embeds.append(
                ModelValidationFindingEmbed(
                    validator_id=request.hook_id,
                    severity="FAIL",
                    location=location,
                    message=f"{location}: [{finding.rule}] {finding.message}",
                    remediation=request.remediation,
                )
            )
        for entry in comparison.stale:
            embeds.append(
                ModelValidationFindingEmbed(
                    validator_id=request.hook_id,
                    severity="FAIL",
                    location=entry.path,
                    message=(
                        f"{entry.path}: stale baseline entry [{entry.rule}] "
                        f"{entry.text!r} has no finding any more; run the hook with "
                        "--write-baseline to shrink the baseline"
                    ),
                    remediation=_STALE_REMEDIATION,
                )
            )
        return ModelValidationReport.from_findings(
            findings=tuple(embeds),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(request.hook_id,),
        )

    def compare(
        self,
        findings: Sequence[ModelSourceFinding],
        entries: Sequence[ModelFindingBaselineEntry],
        scope: ModelFindingBaselineScope,
    ) -> ModelFindingBaselineComparison:
        """Match findings to entries as a multiset keyed by (path, rule, text)."""
        unbaselinable = tuple(f for f in findings if not f.baselinable)
        baselinable = [f for f in findings if f.baselinable]
        covered = Counter(entry.key() for entry in entries)
        used: Counter[tuple[str, str, str]] = Counter()
        new: list[ModelSourceFinding] = []
        for finding in baselinable:
            key = finding.key()
            if used[key] < covered[key]:
                used[key] += 1
            else:
                new.append(finding)
        unjudged = {f.path for f in unbaselinable}
        budget = Counter(f.key() for f in baselinable)
        stale: list[ModelFindingBaselineEntry] = []
        for entry in sorted(entries, key=lambda e: e.key()):
            if not scope.contains(entry.path) or entry.path in unjudged:
                continue
            if budget[entry.key()] > 0:
                budget[entry.key()] -= 1
            else:
                stale.append(entry)
        return ModelFindingBaselineComparison(
            new=tuple(new), stale=tuple(stale), unbaselinable=unbaselinable
        )

    def shrink(
        self,
        findings: Sequence[ModelSourceFinding],
        entries: Sequence[ModelFindingBaselineEntry],
        scope: ModelFindingBaselineScope,
    ) -> ModelFindingBaselineShrink:
        """The entries that survive a rewrite; a finding no entry covers is ``added``."""
        comparison = self.compare(findings, entries, scope)
        dropped = Counter(entry.key() for entry in comparison.stale)
        kept: list[ModelFindingBaselineEntry] = []
        for entry in entries:
            if dropped[entry.key()] > 0:
                dropped[entry.key()] -= 1
                continue
            kept.append(entry)
        return ModelFindingBaselineShrink(
            kept=tuple(kept),
            added=comparison.new,
            unbaselinable=comparison.unbaselinable,
        )

    def create(
        self, hook_id: str, findings: Sequence[ModelSourceFinding]
    ) -> ModelFindingBaseline:
        """A first baseline recording every baselinable finding."""
        return ModelFindingBaseline(
            hook=hook_id,
            entries=tuple(
                ModelFindingBaselineEntry(path=f.path, rule=f.rule, text=f.text)
                for f in findings
                if f.baselinable
            ),
        )

    def render(self, baseline: ModelFindingBaseline) -> str:
        """The committed document, entries sorted by (path, rule, text)."""
        ordered = sorted(baseline.entries, key=lambda e: e.key())
        document = {
            "schema_version": baseline.schema_version,
            "hook": baseline.hook,
            "entries": [entry.model_dump(mode="json") for entry in ordered],
        }
        body = yaml.safe_dump(
            document,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=10_000,
        )
        return _HEADER.format(hook=baseline.hook) + "---\n" + body
