# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Aggregate report model for re-probe verification (OMN-9789).

Emitted by
:func:`omnibase_core.validation.validator_receipt_reprobe.verify_receipts_by_reexecuting_probes`
to summarise the outcome of re-running every recorded ``probe_command``
under a directory tree of receipts. Frozen — once produced it is an
audit artifact.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.ticket.model_receipt_reprobe_result import (
    ModelReceiptReprobeResult,
    ReprobeStatus,
)


class ModelReceiptReprobeReport(BaseModel):
    """Aggregate report of re-probing every receipt under a tree."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    receipts_dir: str = Field(
        ...,
        min_length=1,
        description="Root directory that was walked.",
    )
    results: list[ModelReceiptReprobeResult] = Field(
        default_factory=list,
        description="One result per receipt file discovered. Empty if no receipts.",
    )

    @property
    def passed(self) -> bool:
        """True iff every result is PASS (or there are no results)."""
        return all(r.status == ReprobeStatus.PASS for r in self.results)

    @property
    def failures(self) -> list[ModelReceiptReprobeResult]:
        """All non-PASS results, in walk order."""
        return [r for r in self.results if r.status != ReprobeStatus.PASS]


__all__ = ["ModelReceiptReprobeReport"]
