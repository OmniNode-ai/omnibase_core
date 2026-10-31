# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The document a consumer hands the lab-receipt validator (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_lab_receipt_phase import EnumLabReceiptPhase
from omnibase_core.models.lab_receipt.model_lab_receipt_facts import (
    ModelLabReceiptFacts,
)


class ModelLabReceiptDocument(BaseModel):
    """A phase and the facts to judge in it; the file form of the check input."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    phase: EnumLabReceiptPhase = Field(description="Which rows apply to this run")
    facts: ModelLabReceiptFacts = Field(description="Facts about one pull request")
