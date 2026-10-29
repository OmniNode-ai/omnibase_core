# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Verdict of one shrink-only baseline comparison (OMN-21503)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelShrinkOnlyVerdict"]


class ModelShrinkOnlyVerdict(BaseModel):
    """Result of comparing current fingerprints against a committed baseline.

    ``added`` are fingerprints present now and absent from the baseline (new
    debt). ``stale`` are baseline fingerprints no longer present (the baseline
    should shrink). ``raised`` are baseline fingerprints absent from the
    previous baseline (the baseline itself grew), empty when no previous
    baseline was supplied.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(description="The baseline's kind, for example 'threshold'")
    current_count: int = Field(ge=0, description="Fingerprints present now")
    baseline_count: int = Field(ge=0, description="Fingerprints in the baseline")
    previous_count: int | None = Field(
        default=None, ge=0, description="Fingerprints in the previous baseline"
    )
    added: tuple[str, ...] = Field(
        default=(), description="Present now, absent from the baseline"
    )
    stale: tuple[str, ...] = Field(
        default=(), description="In the baseline, no longer present"
    )
    raised: tuple[str, ...] = Field(
        default=(), description="In the baseline, absent from the previous baseline"
    )

    @property
    def ok(self) -> bool:
        return not self.added and not self.raised
