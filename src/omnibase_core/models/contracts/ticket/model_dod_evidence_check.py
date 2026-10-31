# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodEvidenceCheck — a single check entry within a DoD evidence item. OMN-8916, OMN-10241"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.ticket.enum_dod_check_type import EnumDodCheckType
from omnibase_core.models.contracts.ticket.model_dod_lab_receipt_check_value import (
    ModelDodLabReceiptCheckValue,
)


class ModelDodEvidenceCheck(BaseModel):
    """A single verifiable check within a DoD evidence item.

    check_type must be an EnumDodCheckType value (12 check types supported).
    check_value is either a plain string command/path or a dict[str, str] for structured checks (e.g. grep pattern+path).
    cwd supports template tokens: ${OMNI_HOME}, ${PR_NUMBER}, ${REPO}, ${TICKET_ID}.
    A lab_receipt check's check_value must be the typed shape of
    ModelDodLabReceiptCheckValue (OMN-21831).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_type: EnumDodCheckType
    check_value: str | dict[str, str]
    cwd: str | None = Field(
        default=None,
        description="Optional working directory. Supports ${OMNI_HOME}, ${PR_NUMBER}, ${REPO}, ${TICKET_ID} tokens.",
    )

    @model_validator(mode="after")
    def validate_lab_receipt_shape(self) -> ModelDodEvidenceCheck:
        """Refuse a lab_receipt check whose value is missing a field or has an unknown one."""
        if self.check_type is EnumDodCheckType.LAB_RECEIPT:
            ModelDodLabReceiptCheckValue.model_validate(self.check_value)
        return self


__all__ = ["ModelDodEvidenceCheck"]
