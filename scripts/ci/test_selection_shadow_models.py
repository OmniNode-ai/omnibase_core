# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Frozen output contract for shadow-mode test-selection measurement (OMN-14342).

A ``ModelShadowRecord`` is the per-PR counterfactual: what the change-aware
selector WOULD have picked (forced on) versus what the full suite actually ran.
It is observational only — the full suite still runs on the boundary; this record
never changes what executes. One record per dev PR is appended to the durable
``ci-shadow-metrics`` NDJSON log so the selector's real-world miss-rate can be
measured before it is trusted as the dev default.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHADOW_RECORD_SCHEMA_VERSION = 1


class ModelShadowRecord(BaseModel):
    """One dev-PR shadow measurement, serialized as a single NDJSON line."""

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    schema_version: int = Field(default=SHADOW_RECORD_SCHEMA_VERSION, ge=1)

    # Provenance
    repo: str
    pr_number: int | None = None
    head_sha: str
    base_sha: str | None = None
    event: str
    ref_name: str
    created_at: str  # ISO-8601 UTC, when the record was built

    # Change set
    changed_file_count: int = Field(..., ge=0)
    changed_modules: list[str] = Field(default_factory=list)

    # What the selector (forced on) would have done
    shadow_is_full_suite: bool
    shadow_reason: str | None = None  # EnumFullSuiteReason value, or None when narrowed
    triggering_shared_modules: list[str] = Field(default_factory=list)
    predicted_paths: list[str] = Field(default_factory=list)
    predicted_split_count: int = Field(..., ge=1, le=40)

    # Full-suite actuals (unit job only — integration always runs, never narrowed)
    total_test_files: int = Field(..., ge=0)
    selected_test_files: int = Field(..., ge=0)
    selected_fraction: float = Field(..., ge=0.0, le=1.0)
    full_suite_test_count: int = Field(..., ge=0)
    full_suite_failure_count: int = Field(..., ge=0)

    # THE safety metric: full-suite failures whose test file the shadow set would
    # have skipped. Must be 0 for the narrowed selection to be trustworthy.
    escaped_failures: list[str] = Field(default_factory=list)
    escaped_failure_count: int = Field(..., ge=0)

    # Wall-clock accounting (seconds), summed from junit per-test timings
    wall_clock_total_s: float = Field(..., ge=0.0)
    wall_clock_selected_s: float = Field(..., ge=0.0)
    wall_clock_saved_s: float = Field(..., ge=0.0)

    junit_files_parsed: int = Field(..., ge=0)

    @model_validator(mode="after")
    def _check_internal_consistency(self) -> Self:
        if self.selected_test_files > self.total_test_files:
            raise ValueError(
                f"selected_test_files ({self.selected_test_files}) exceeds "
                f"total_test_files ({self.total_test_files})"
            )
        if self.escaped_failure_count != len(self.escaped_failures):
            raise ValueError(
                f"escaped_failure_count ({self.escaped_failure_count}) != "
                f"len(escaped_failures) ({len(self.escaped_failures)})"
            )
        if self.escaped_failure_count > self.full_suite_failure_count:
            raise ValueError(
                f"escaped_failure_count ({self.escaped_failure_count}) exceeds "
                f"full_suite_failure_count ({self.full_suite_failure_count})"
            )
        # When the shadow selection was itself a full suite, nothing is skipped:
        # no failure can escape and no wall-clock is saved.
        if self.shadow_is_full_suite:
            if self.escaped_failure_count != 0:
                raise ValueError(
                    "escaped_failure_count must be 0 when shadow_is_full_suite=True"
                )
            if self.wall_clock_saved_s != 0.0:
                raise ValueError(
                    "wall_clock_saved_s must be 0 when shadow_is_full_suite=True"
                )
        return self
