# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelBreakingSchemaFinding — finding from the breaking-schema-change validator (OMN-12621)."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelBreakingSchemaFinding(BaseModel):
    """A single finding from the breaking-schema-change validator."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: Path = Field(
        ..., description="Topic-schema declaration that changed breakingly"
    )
    rule: str = Field(..., description="Validator rule that fired")
    delta: str = Field(..., description="Detected breaking delta classification")
    message: str = Field(..., description="Human-readable explanation")

    def format(self) -> str:
        return f"{self.path}: [{self.rule}] ({self.delta}) {self.message}"


__all__ = ["ModelBreakingSchemaFinding"]
