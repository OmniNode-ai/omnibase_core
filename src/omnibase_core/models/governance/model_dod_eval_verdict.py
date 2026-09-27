# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed result of the shared definition-of-done evaluation."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.governance.enum_dod_eval_outcome import EnumDodEvalOutcome
from omnibase_core.enums.governance.enum_dod_eval_refusal import EnumDodEvalRefusal


class ModelDodEvalVerdict(BaseModel):
    """Whether one verification counts as done and, when refused, why."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: EnumDodEvalOutcome = Field(..., description="Done, or refused.")
    refusal: EnumDodEvalRefusal | None = Field(
        default=None,
        description="Which conjunct failed. Set exactly when outcome is refused.",
    )

    @model_validator(mode="after")
    def _refusal_pairs_with_refused(self) -> Self:
        """A refusal names its reason, and a done outcome names none."""
        refused = self.outcome is EnumDodEvalOutcome.REFUSED
        if refused != (self.refusal is not None):
            msg = (
                "refusal is set exactly when outcome is REFUSED; got "
                f"outcome={self.outcome.value}, refusal={self.refusal!r}"
            )
            raise ValueError(msg)
        return self

    @property
    def is_done(self) -> bool:
        """True only for a completed, evidence-bearing verification."""
        return self.outcome is EnumDodEvalOutcome.DONE


__all__ = ["ModelDodEvalVerdict"]
