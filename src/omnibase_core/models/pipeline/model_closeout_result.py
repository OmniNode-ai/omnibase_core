# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Closeout result model for pipeline verification."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.pipeline.enum_closeout_failure import EnumCloseoutFailure
from omnibase_core.models.pipeline.model_chain_diff import ModelChainDiff
from omnibase_core.models.pipeline.model_evidence_artifact import ModelEvidenceArtifact

__all__ = ["ModelCloseoutResult"]


class ModelCloseoutResult(BaseModel):
    """Full result of a pipeline closeout verification."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    passed: bool
    chain_match: bool
    chain_diff: ModelChainDiff | None = None
    evidence_artifacts: tuple[ModelEvidenceArtifact, ...] = Field(default_factory=tuple)
    missing_evidence: tuple[str, ...] = Field(default_factory=tuple)
    test_result: bool = True
    failure_class: EnumCloseoutFailure | None = None
    verifier_identity: str | None = None
