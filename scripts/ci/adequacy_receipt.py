# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Coverage-guided compute-golden adequacy receipt (OMN-14353 f/u, Task #41).

Turns the proven ``compute_golden`` primitive into the load-bearing feature: a
recorder whose golden set is chosen to MEASURE UP TO its promise. The canary
showed a golden set at 49.9% branch coverage let 2 of 3 goldens miss a
regression, so a happy-path golden must not be enough to mark a node canonical.

This module:
  * greedily selects, from a candidate input pool, the minimal subset that
    maximizes the legacy handler's BRANCH coverage (Fable gap #1);
  * stamps provenance (handler-module sha256, recorded_at, per-input hash) —
    porting ``golden_chain.record_fixture``'s one genuinely reusable idea;
  * applies a DENY-BY-DEFAULT scrub over recorded payloads (gap #5);
  * emits a ``ModelAdequacyReceipt`` (coverage % + target + volatile mask +
    provenance + explicit uncovered waiver) — the artifact the canonical-shape
    ratchet-gate flip consumes, so "canonical" means coverage-measured.

Property-based / contract-driven synthesis of NEW inputs for branches live
traffic never reaches is the remaining half (design reported separately); this
module consumes whatever candidate pool it is given and proves how much of the
handler that pool actually exercises.
"""

from __future__ import annotations

import functools
import hashlib
import io
import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, Self

import coverage
from pydantic import BaseModel, ConfigDict, Field, model_validator

RECEIPT_VERSION = "adequacy_receipt.v1"
DEFAULT_COVERAGE_TARGET = 80.0

# Deny-by-default scrub: any dict key whose lowercased name contains one of these
# substrings has its value redacted before the payload is persisted.
_DEFAULT_SCRUB_SUBSTRINGS = (
    "secret",
    "token",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "private_key",
    "credential",
    "authorization",
)
_SCRUBBED = "<scrubbed>"


class _JsonDumpable(Protocol):
    def model_dump(self, *, mode: str = ...) -> dict[str, Any]: ...


class ModelUncoveredWaiver(BaseModel):
    """Explicit, reviewed acknowledgement that coverage fell short of target."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    reason: str = Field(..., min_length=1)
    uncovered_branch_count: int = Field(..., ge=0)


class ModelAdequacyReceipt(BaseModel):
    """The adequacy artifact the canonical-shape gate consumes."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    # Schema discriminator tags (NOT semver) — the recorder's on-disk format id.
    receipt_schema: str = Field(default=RECEIPT_VERSION)
    node_id: str
    handler_module: str
    handler_module_sha256: str
    recorded_at: str
    recorder_schema: str = Field(default=RECEIPT_VERSION)

    candidate_count: int = Field(..., ge=0)
    selected_count: int = Field(..., ge=0)
    selected_input_hashes: list[str] = Field(default_factory=list)

    # coverage.py's total percent with branch=True: statements + branches
    # (branch-inclusive), scoped to the handler module only.
    branch_coverage_pct: float = Field(..., ge=0.0, le=100.0)
    coverage_target: float = Field(default=DEFAULT_COVERAGE_TARGET, ge=0.0, le=100.0)
    meets_target: bool
    uncovered_waiver: ModelUncoveredWaiver | None = None

    volatile_mask: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.selected_count > self.candidate_count:
            raise ValueError("selected_count exceeds candidate_count")
        if self.selected_count != len(self.selected_input_hashes):
            raise ValueError("selected_count != len(selected_input_hashes)")
        if self.meets_target and self.uncovered_waiver is not None:
            raise ValueError("uncovered_waiver forbidden when meets_target=True")
        if not self.meets_target and self.uncovered_waiver is None:
            raise ValueError(
                "meets_target=False requires an explicit uncovered_waiver "
                "(a node below target cannot be marked canonical silently)"
            )
        if self.meets_target and self.selected_count == 0:
            # Degenerate pass: coverage cannot be certified met over zero inputs
            # (e.g. target=0 with an empty pool). Flagged by canon-inventory's
            # seam review — the gate must not accept an input-less "pass".
            raise ValueError(
                "meets_target=True requires selected_count >= 1 "
                "(coverage cannot be certified over zero inputs)"
            )
        return self


def handler_module_sha256(module_file: str | Path) -> str:
    """Hash the handler's source file — pins the receipt to the exact legacy code."""
    return "sha256:" + hashlib.sha256(Path(module_file).read_bytes()).hexdigest()


def input_hash(input_model: _JsonDumpable) -> str:
    """Canonical sha256 of a serialized input (stable regardless of key order)."""
    canon = json.dumps(input_model.model_dump(mode="json"), sort_keys=True)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def scrub(payload: Any, substrings: Sequence[str] = _DEFAULT_SCRUB_SUBSTRINGS) -> Any:
    """Deep deny-by-default redaction of sensitive-looking dict values."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(key, str) and any(s in key.lower() for s in substrings):
                out[key] = _SCRUBBED
            else:
                out[key] = scrub(value, substrings)
        return out
    if isinstance(payload, list):
        return [scrub(item, substrings) for item in payload]
    return payload


def _measured_arcs(
    run: Callable[[], object], source_match: str
) -> set[tuple[str, int, int]]:
    """Branch arcs exercised by ``run()``, restricted to files matching ``source_match``."""
    # config_file=False so the repo's [tool.coverage] source/omit does not scope us.
    cov = coverage.Coverage(branch=True, config_file=False)
    cov.start()
    try:
        run()
    finally:
        cov.stop()
    data = cov.get_data()
    arcs: set[tuple[str, int, int]] = set()
    for filename in data.measured_files():
        if source_match not in filename:
            continue
        for a0, a1 in data.arcs(filename) or []:
            arcs.add((filename, a0, a1))
    return arcs


def select_covering(
    *,
    handler_call: Callable[[Any], Any],
    candidates: Sequence[Any],
    source_match: str,
) -> tuple[list[int], set[tuple[str, int, int]]]:
    """Greedily pick the minimal candidate subset maximizing branch arcs.

    Returns (selected indices in pick order, the union of arcs they cover).
    Deterministic: ties broken by candidate index.
    """
    per_candidate: list[set[tuple[str, int, int]]] = [
        _measured_arcs(functools.partial(handler_call, c), source_match)
        for c in candidates
    ]
    covered: set[tuple[str, int, int]] = set()
    selected: list[int] = []
    remaining = set(range(len(candidates)))
    while remaining:
        best_idx = -1
        best_gain = 0
        for idx in sorted(remaining):
            gain = len(per_candidate[idx] - covered)
            if gain > best_gain:
                best_gain = gain
                best_idx = idx
        if best_idx < 0 or best_gain == 0:
            break
        selected.append(best_idx)
        covered |= per_candidate[best_idx]
        remaining.discard(best_idx)
    return selected, covered


def coverage_pct_for(*, run: Callable[[], object], source_match: str) -> float:
    """Overall branch-coverage percent for ``run()`` over files matching source_match.

    Uses coverage.py's documented ``report()`` return value (the total percent,
    branch-inclusive when ``branch=True``), scoped via an ``include`` glob.
    """
    # config_file=False so the repo's [tool.coverage] source does not scope us;
    # report() is then given the explicit measured handler files (morfs) so the
    # percent is for the handler alone, not diluted across the package.
    cov = coverage.Coverage(branch=True, config_file=False)
    cov.start()
    try:
        run()
    finally:
        cov.stop()
    morfs = [f for f in cov.get_data().measured_files() if source_match in f]
    if not morfs:
        return 0.0
    sink = io.StringIO()
    try:
        return round(float(cov.report(morfs=morfs, file=sink)), 2)
    except coverage.exceptions.NoDataError:
        return 0.0


def build_receipt(
    *,
    node_id: str,
    handler_module_file: str | Path,
    handler_call: Callable[[Any], Any],
    candidates: Sequence[_JsonDumpable],
    source_match: str,
    volatile_mask: list[str] | None = None,
    coverage_target: float = DEFAULT_COVERAGE_TARGET,
    waiver_reason: str | None = None,
) -> ModelAdequacyReceipt:
    """Coverage-guided selection → adequacy receipt for one COMPUTE node."""
    selected_idx, _covered_arcs = select_covering(
        handler_call=handler_call, candidates=candidates, source_match=source_match
    )
    selected = [candidates[i] for i in selected_idx]

    def _run_selected() -> None:
        for candidate in selected:
            handler_call(candidate)

    pct = coverage_pct_for(run=_run_selected, source_match=source_match)
    meets = pct >= coverage_target
    waiver = None
    if not meets:
        waiver = ModelUncoveredWaiver(
            reason=waiver_reason
            or (
                f"candidate pool reaches only {pct:.1f}% branch coverage "
                f"(< {coverage_target:.0f}% target); pool needs coverage-guided "
                "synthesis for the uncovered branches"
            ),
            uncovered_branch_count=0,
        )
    return ModelAdequacyReceipt(
        node_id=node_id,
        handler_module=str(handler_module_file),
        handler_module_sha256=handler_module_sha256(handler_module_file),
        recorded_at=datetime.now(UTC).isoformat(),
        candidate_count=len(candidates),
        selected_count=len(selected),
        selected_input_hashes=[input_hash(c) for c in selected],
        branch_coverage_pct=pct,
        coverage_target=coverage_target,
        meets_target=meets,
        uncovered_waiver=waiver,
        volatile_mask=list(volatile_mask or []),
    )


__all__ = [
    "DEFAULT_COVERAGE_TARGET",
    "ModelAdequacyReceipt",
    "ModelUncoveredWaiver",
    "build_receipt",
    "handler_module_sha256",
    "input_hash",
    "scrub",
    "select_covering",
]
