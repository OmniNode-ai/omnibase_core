# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed test inventory from one or more JUnit reports."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.skip_count_ratchet_check.model_skip_count_record import (
    ModelSkipCountRecord,
)


class ModelSkipCountObservation(BaseModel):
    """Collection totals and individual records; skips are deduplicated."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    records: tuple[ModelSkipCountRecord, ...]
    collected: int
    files: int

    @property
    def test_records(self) -> int:
        return len(self.records)

    @property
    def skipped(self) -> frozenset[str]:
        return frozenset(
            r.identity[6:] if r.identity.startswith("tests.") else r.identity
            for r in self.records
            if r.skipped
        )

    @property
    def count(self) -> int:
        return len(self.skipped)
