# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Batch validation summary model (OMN-9769, parent OMN-9757).

Aggregated result produced by :func:`omnibase_core.normalization.batch_validator.run_batch_validation`.
One instance per directory sweep; contains per-file reports and pass/fail counts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_validator_mode import EnumValidatorMode
from omnibase_core.models.contracts.model_corpus_validation_report import (
    ModelCorpusValidationReport,
)


class ModelBatchValidationSummary(BaseModel):
    """Aggregated result from a batch contract validation sweep.

    Frozen so callers can treat the summary as an immutable evidence record.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    total: int
    passed: int
    failed: int
    mode: EnumValidatorMode
    reports: list[ModelCorpusValidationReport] = Field(default_factory=list)


__all__ = ["ModelBatchValidationSummary"]
