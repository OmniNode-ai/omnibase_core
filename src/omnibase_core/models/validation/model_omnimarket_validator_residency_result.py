# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of one omnimarket validator residency check (OMN-21503)."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue

__all__ = ["ModelOmnimarketValidatorResidencyResult"]


class ModelOmnimarketValidatorResidencyResult(BaseModel):
    """Counted residents and the issues found; byte-stable when serialized."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    resident_validators: tuple[str, ...] = Field(
        description="Resident ids counted as validator predicates, sorted"
    )
    count: int = Field(ge=0, description="len(resident_validators)")
    unclassified: tuple[str, ...] = Field(
        default=(), description="Residents the inventory does not list, sorted"
    )
    issues: tuple[ModelValidationIssue, ...] = Field(
        default=(), description="Issues in deterministic order"
    )

    @property
    def ok(self) -> bool:
        return not any(
            issue.severity.value in {"error", "critical", "fatal"}
            for issue in self.issues
        )

    def canonical_json(self) -> str:
        """Sorted-key compact JSON, identical across processes and entries."""
        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
