# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelCorpusClassification — pre-validation classification result (OMN-9760, parent OMN-9757).

Output of the corpus classifier (see ``omnibase_core.normalization.corpus_classifier``).
Records which bucket a contract YAML file maps to before the per-family
normalization + strict Pydantic validation pipeline runs.

Distinct from:
    * ``ModelContractLoadResult`` — runtime loader result wrapper
    * ``ModelCorpusStatistics`` — replay-domain corpus stats
    * ``ModelContractValidationResult`` — code-generation scoring/feedback
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket


class ModelCorpusClassification(BaseModel):
    """Classification verdict for a single contract YAML file.

    ``confidence`` is ``None`` when the classification is certain; populated
    in [0.0, 1.0] when path/shape signals disagree or no glob matched. Path
    classification is the primary signal — shape inspection adjusts confidence
    and appends ``reasons`` but never overrides the path-derived bucket.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: Path
    bucket: EnumContractBucket
    raw_node_type: str | None = None
    requires_validation: bool
    reasons: list[str] = Field(default_factory=list)
    confidence: float | None = None
    notes: list[str] = Field(default_factory=list)


__all__ = ["ModelCorpusClassification"]
