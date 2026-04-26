# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-file corpus validation report (OMN-9767, parent OMN-9757).

Phase 3 of the corpus classification and normalization layer.

``ModelCorpusValidationReport`` is the per-file outcome record produced
by the corpus contract validator. One instance per ``contract.yaml``
walked. Aggregates of these power the migration-audit summary (counts
by bucket, by mode, pass/fail rates, normalized-vs-not breakdowns).

Distinct from:

- ``ModelValidationReport`` (omnibase_core/models/validation) — a
  generic validator-framework aggregator with severity precedence,
  metrics, and provenance (OMN-2362). Different semantic domain.
- ``ModelContractValidationResult`` — a scoring/feedback artifact for
  code-generation systems with score + suggestions fields.

This model is intentionally narrow to the corpus-sweep use case:
``path``, ``bucket``, ``mode``, ``passed``, ``errors``, ``normalized``,
``normalization_flags``. No score, no suggestions, no severity.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket
from omnibase_core.enums.enum_validator_mode import EnumValidatorMode


class ModelCorpusValidationReport(BaseModel):
    """Single-file outcome record from the corpus contract validator.

    Frozen, extra=forbid: instances are immutable evidence rows that the
    batch validator collects into a list and the audit summarizer
    aggregates without further mutation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: Path
    bucket: EnumContractBucket
    mode: EnumValidatorMode
    passed: bool
    errors: list[str] = Field(default_factory=list)
    normalized: bool
    normalization_flags: list[str] = Field(default_factory=list)


__all__ = ["ModelCorpusValidationReport"]
