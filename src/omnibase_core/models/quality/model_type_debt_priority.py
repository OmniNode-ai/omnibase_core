# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelTypeDebtPriority — LLM scorer output for a single finding.

Emitted by both Track A (ADK agent) and Track B (omnimarket POC handler)
for every finding they prioritize. Packaged inside a ModelTypeDebtReport.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_type_debt_priority import EnumTypeDebtPriority


class ModelTypeDebtPriority(BaseModel):
    """LLM-assigned priority + rationale for a single type-debt finding."""

    finding_ref: str = Field(
        ...,
        min_length=1,
        description=(
            "Identifier pointing back to the mypy/ruff finding this scores "
            "(canonical form: 'file.py:line')."
        ),
    )
    priority: EnumTypeDebtPriority = Field(
        ...,
        description="Priority tier assigned by the LLM scorer.",
    )
    rationale: str = Field(
        ...,
        min_length=1,
        description="One-sentence justification for the assigned priority.",
    )
    fix_sketch: str | None = Field(
        default=None,
        description="Optional short suggested fix; None when the LLM declined to suggest.",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelTypeDebtPriority"]
