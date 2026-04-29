# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelVerifierOutput — output from the deterministic verification layer (OMN-10251)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.overseer.enum_failure_class import EnumFailureClass
from omnibase_core.enums.overseer.enum_verifier_verdict import EnumVerifierVerdict
from omnibase_core.models.contracts.ticket.model_dod_receipt import (
    ModelDodReceipt,
)


class ModelVerifierOutput(BaseModel):
    """Output from the deterministic verification layer.

    Contains the overall verdict, per-check results (as ModelDodReceipt), and
    optional shim outputs for downstream consumers.

    Per OMN-9792: checks items migrated from ModelVerifierCheckResult to
    ModelDodReceipt.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    verdict: EnumVerifierVerdict = Field(
        ..., description="Overall verification verdict."
    )
    checks: tuple[ModelDodReceipt, ...] = Field(
        default_factory=tuple, description="Per-check results as canonical receipts."
    )
    failure_class: EnumFailureClass | None = Field(
        default=None,
        description="Dominant failure class when verdict is not PASS.",
    )
    shim_outputs: dict[str, str] = Field(
        default_factory=dict,
        description="Opaque key-value outputs for downstream shim consumers.",
    )
    summary: str = Field(
        default="", description="Human-readable summary of verification results."
    )

    @model_validator(mode="after")
    def validate_verdict_consistency(self) -> ModelVerifierOutput:
        if self.verdict == EnumVerifierVerdict.PASS and self.failure_class is not None:
            msg = "failure_class must be None when verdict=PASS"
            raise ValueError(
                msg
            )  # error-ok: Pydantic model_validator requires ValueError
        return self


__all__ = ["ModelVerifierOutput"]
