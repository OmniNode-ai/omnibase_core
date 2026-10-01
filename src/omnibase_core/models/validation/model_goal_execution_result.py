# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed, contract-owned pins for cross-repository goal evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.constants.constants_goal_admission import (
    _SHA256_RE,
)
from omnibase_core.models.validation.model_goal_check_execution_outcome import (
    ModelGoalCheckExecutionOutcome,
)
from omnibase_core.models.validation.model_goal_criterion_execution_evidence import (
    ModelGoalCriterionExecutionEvidence,
)
from omnibase_core.models.validation.model_goal_selector_execution_outcome import (
    ModelGoalSelectorExecutionOutcome,
)


class ModelGoalExecutionResult(BaseModel):
    """Canonical produced result R; it exists before the final admission stamp."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    attempt_id: UUID
    criterion_evidence: tuple[ModelGoalCriterionExecutionEvidence, ...] = Field(
        ..., min_length=1
    )
    raw_check_outcomes: tuple[ModelGoalCheckExecutionOutcome, ...] = Field(
        ..., min_length=1
    )
    selector_outcomes: tuple[ModelGoalSelectorExecutionOutcome, ...] = Field(
        ..., min_length=1
    )
    artifact_sha256: tuple[str, ...] = Field(..., min_length=1)

    @field_validator("artifact_sha256")
    @classmethod
    def _artifacts_are_canonical(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not _SHA256_RE.fullmatch(value) for value in values):
            raise ValueError("artifact digests must use sha256:<64 lowercase hex>")
        if len(set(values)) != len(values):
            raise ValueError("artifact digests must be unique")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def _criterion_ids_are_unique(self) -> Self:
        ids = [record.criterion_id for record in self.criterion_evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("execution result criterion ids must be unique")
        raw_ids = [
            (record.criterion_id, record.item_id, record.check_type)
            for record in self.raw_check_outcomes
        ]
        if len(raw_ids) != len(set(raw_ids)):
            raise ValueError("execution result raw check outcomes must be unique")
        selectors = [item.selector for item in self.selector_outcomes]
        if len(selectors) != len(set(selectors)):
            raise ValueError("execution result selectors must be unique")
        return self

    def content_sha256(self) -> str:
        payload = {
            "attempt_id": str(self.attempt_id),
            "criterion_evidence": [
                item.model_dump(mode="json")
                for item in sorted(
                    self.criterion_evidence, key=lambda item: item.criterion_id
                )
            ],
            "raw_check_outcomes": [
                item.model_dump(mode="json")
                for item in sorted(
                    self.raw_check_outcomes,
                    key=lambda item: (
                        item.criterion_id,
                        item.item_id,
                        item.check_type.value,
                    ),
                )
            ],
            "selector_outcomes": [
                item.model_dump(mode="json")
                for item in sorted(
                    self.selector_outcomes, key=lambda item: item.selector
                )
            ],
            "artifact_sha256": sorted(self.artifact_sha256),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
