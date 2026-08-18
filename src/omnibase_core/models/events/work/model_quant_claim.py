# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Quantitative claim with its provenance (OMN-16177).

The load-bearing schema move of the work-event increment: OMN-15897's
write-time regex lint over ledger prose becomes a typed field with a required
``probe_command``. A number cannot be emitted without the command that produced
it, because the field carrying the number also requires that command. A rule
becomes a mechanism.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import AwareDatetime, Field, field_validator

from omnibase_core.models.events.model_event_payload_base import ModelEventPayloadBase

__all__ = ["ModelQuantClaim"]


class ModelQuantClaim(ModelEventPayloadBase):
    """One measured number, with the probe and moment that produced it."""

    value: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description=(
            "The measured value as observed, verbatim. Kept as a string so a "
            "count, a duration, and a ratio round-trip without lossy coercion."
        ),
    )
    unit: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="What the value counts, e.g. 'rows', 'topics', 'seconds'.",
    )
    probe_command: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description=(
            "The command that produced this value. Required: an unverified "
            "number has no place in the record."
        ),
    )
    observed_at: AwareDatetime = Field(
        ...,
        description="When the probe ran. Timezone-aware; no wall-clock default.",
    )

    @field_validator("value", "unit", "probe_command")
    @classmethod
    def _reject_blank(cls, raw: str) -> str:
        """Whitespace is not a value, a unit, or a probe."""
        if not raw.strip():
            raise ValueError("must not be blank or whitespace-only")
        return raw

    @field_validator("observed_at")
    @classmethod
    def _reject_naive(cls, raw: datetime) -> datetime:
        if raw.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        return raw
