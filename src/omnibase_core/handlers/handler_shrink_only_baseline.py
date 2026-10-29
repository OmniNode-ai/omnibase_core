# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shrink-only baseline comparison (OMN-21503, T-Q6).

Pure: typed facts in (fingerprint multisets), verdict and
``ModelValidationIssue`` items out, no I/O. Shared by the omnimarket validator
residency ratchet and by the hard-coded-value rules that T-Q6 extends
(ruling stamp, model name, host name, numeric threshold), so every kind is
judged against its own baseline by the same rule: a fingerprint absent from the
baseline fails, and a baseline that holds a fingerprint its previous revision
did not hold fails.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.validation.model_shrink_only_verdict import (
    ModelShrinkOnlyVerdict,
)

__all__ = [
    "compare_shrink_only",
    "finding_fingerprint",
    "load_fingerprint_baseline",
    "unbaselined_mask",
    "verdict_issues",
]

_CODE_ADDED = "baseline_added"
_CODE_RAISED = "baseline_raised"


def _expand(counter: Counter[str]) -> tuple[str, ...]:
    return tuple(sorted(counter.elements()))


def compare_shrink_only(
    kind: str,
    current: Iterable[str],
    baseline: Iterable[str],
    previous_baseline: Iterable[str] | None = None,
) -> ModelShrinkOnlyVerdict:
    """Compare ``current`` fingerprints with ``baseline`` as multisets."""
    cur = Counter(current)
    base = Counter(baseline)
    prev = Counter(previous_baseline) if previous_baseline is not None else None
    return ModelShrinkOnlyVerdict(
        kind=kind,
        current_count=sum(cur.values()),
        baseline_count=sum(base.values()),
        previous_count=sum(prev.values()) if prev is not None else None,
        added=_expand(cur - base),
        stale=_expand(base - cur),
        raised=_expand(base - prev) if prev is not None else (),
    )


def verdict_issues(
    verdict: ModelShrinkOnlyVerdict, *, baseline_path: Path | None = None
) -> tuple[ModelValidationIssue, ...]:
    """One error issue per added fingerprint and per raised baseline entry."""
    issues: list[ModelValidationIssue] = []
    for fingerprint in verdict.added:
        issues.append(
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message=(
                    f"{verdict.kind}: new finding {fingerprint} is not in the "
                    "shrink-only baseline; fix it, do not add it to the baseline"
                ),
                code=_CODE_ADDED,
                file_path=baseline_path,
                rule_name=verdict.kind,
            )
        )
    for fingerprint in verdict.raised:
        issues.append(
            ModelValidationIssue(
                severity=EnumSeverity.ERROR,
                message=(
                    f"{verdict.kind}: baseline entry {fingerprint} was not in the "
                    "previous baseline; a baseline may only shrink"
                ),
                code=_CODE_RAISED,
                file_path=baseline_path,
                rule_name=verdict.kind,
            )
        )
    return tuple(issues)


def load_fingerprint_baseline(path: Path, kind: str) -> list[str]:
    """Read a JSON fingerprint multiset, judging only entries of ``kind``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("entries"), list)
        or not all(isinstance(entry, str) for entry in data["entries"])
    ):
        raise ModelOnexError(
            message="Baseline must contain an entries list of strings",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return [entry for entry in data["entries"] if entry.startswith(f"{kind}|")]


def finding_fingerprint(kind: str, path: Path, line: int) -> str:
    """Stable fingerprint: kind, cwd-relative POSIX path, sha1 of the stripped line."""
    text = path.read_text(encoding="utf-8").splitlines()[line - 1].strip()
    digest = hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()
    relative = Path(os.path.relpath(path.resolve(), Path.cwd())).as_posix()
    return f"{kind}|{relative}|{digest}"


def unbaselined_mask(
    kind: str,
    fingerprints: Sequence[str],
    baseline: Sequence[str],
    previous_baseline: Sequence[str] | None = None,
) -> tuple[list[bool], ModelShrinkOnlyVerdict]:
    """True for each fingerprint the baseline does not cover (multiset order)."""
    verdict = compare_shrink_only(kind, fingerprints, baseline, previous_baseline)
    added = Counter(verdict.added)
    mask: list[bool] = []
    for fingerprint in fingerprints:
        is_new = added[fingerprint] > 0
        if is_new:
            added[fingerprint] -= 1
        mask.append(is_new)
    return mask, verdict
