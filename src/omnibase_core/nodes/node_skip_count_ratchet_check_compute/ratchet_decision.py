# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Exact original verdict lines, shared by handler and CLI presentation."""

from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_baseline_entry import (
    ModelSkipCountBaselineEntry,
)
from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_observation import (
    ModelSkipCountObservation,
)

VALIDATOR_ID = "skip-count-ratchet"
ZERO_RECORDS_MESSAGE = (
    "zero test records observed: a run that scans nothing is ERROR, never PASS"
)


def evaluate(
    entry: ModelSkipCountBaselineEntry, observed: ModelSkipCountObservation
) -> tuple[int, list[str]]:
    """Return (exit code, report lines). Pure — no I/O, no clock, no environment."""
    lines: list[str] = [
        "================================================================",
        f"Skip Count Ratchet (OMN-18776) — {entry.key}",
        f"  repo          : {entry.repo}",
        f"  job           : {entry.job}",
        f"  mode          : {entry.mode}",
        f"  observed      : {observed.count} unique skipped / {observed.collected} "
        f"collected, across {observed.files} JUnit report(s)",
        f"  baseline      : {entry.max_skips} unique skipped / "
        f"{entry.baseline_collected} collected",
        "================================================================",
    ]

    if entry.mode == "nodeids":
        new_ids = sorted(observed.skipped - entry.node_ids)
        if new_ids:
            lines.append(
                f"::error::{entry.repo} / {entry.job}: the skipped set GREW by "
                f"{len(new_ids)} test(s) (delta +{len(new_ids)}; "
                f"{observed.count} observed against a baseline of {entry.max_skips}). "
                f"These tests are collected and never executed, and are not in "
                f"config/skip_count_baseline.yaml:"
            )
            lines.extend(f"    + {i}" for i in new_ids)
            lines.append(
                "  Either make the test run, or record it in the baseline with its "
                "provenance and say in the PR why it may never execute."
            )
            return 1, lines

        narrowed = observed.collected < entry.baseline_collected
        if narrowed:
            lines.append(
                f"  PASS — narrowed selection: the impacted-test selector collected "
                f"{observed.collected} of the baseline's {entry.baseline_collected}, "
                f"so {observed.count} of {entry.max_skips} baseline skips were "
                f"observed. Not a ratchet candidate; the lower number is the "
                f"selector, not progress."
            )
            return 0, lines
        if observed.count < entry.max_skips:
            retired = sorted(entry.node_ids - observed.skipped)
            lines.append(
                f"  RATCHET CANDIDATE — a full-width run skipped {observed.count}, "
                f"below the baseline of {entry.max_skips}. Lower `max_skips` to "
                f"{observed.count} in config/skip_count_baseline.yaml and drop these "
                f"{len(retired)} id(s):"
            )
            lines.extend(f"    - {i}" for i in retired[:25])
            if len(retired) > 25:
                lines.append(f"    ... and {len(retired) - 25} more")
            return 0, lines
        lines.append(f"  PASS — at baseline ({observed.count} of {entry.max_skips}).")
        return 0, lines

    # mode == "count"
    if observed.count > entry.max_skips:
        delta = observed.count - entry.max_skips
        lines.append(
            f"::error::{entry.repo} / {entry.job}: skip count {observed.count} "
            f"exceeds the baseline {entry.max_skips} (delta +{delta})."
        )
        if entry.node_ids:
            new_ids = sorted(observed.skipped - entry.node_ids)
            lines.extend(f"    + {i}" for i in new_ids)
        return 1, lines
    if observed.count < entry.max_skips:
        lines.append(
            f"  RATCHET CANDIDATE — skip count {observed.count} is below the "
            f"baseline of {entry.max_skips}. Lower `max_skips` to {observed.count} "
            f"in config/skip_count_baseline.yaml."
        )
        return 0, lines
    lines.append(f"  PASS — at baseline ({observed.count} of {entry.max_skips}).")
    return 0, lines
