# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result model for the OCC append-only enforcement gate (OMN-13888)."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_append_only_violation_kind import (
    EnumAppendOnlyViolationKind,
)


class ModelAppendOnlyViolation(BaseModel):
    """A single append-only violation with a human-readable detail."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: EnumAppendOnlyViolationKind
    target: str = Field(
        ..., description="dod_evidence item id or receipt file path that violated."
    )
    detail: str = Field(default="")


class ModelOccAppendOnlyResult(BaseModel):
    """Aggregate result of the append-only check over a contract + receipt diff."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: bool
    reason: str = Field(
        default="",
        description="APPEND_ONLY_VIOLATION when ok is False, empty otherwise.",
    )
    violations: tuple[ModelAppendOnlyViolation, ...] = Field(default_factory=tuple)
    detail: str = Field(default="")

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "violations": [
                {"kind": v.kind.value, "target": v.target, "detail": v.detail}
                for v in self.violations
            ],
            "detail": self.detail,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "EnumAppendOnlyViolationKind",
    "ModelAppendOnlyViolation",
    "ModelOccAppendOnlyResult",
]
