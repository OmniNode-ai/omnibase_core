# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelEffectBackendsRequest (OMN-22911)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_effect_contract_document import (
    ModelEffectContractDocument,
)


class ModelEffectBackendsRequest(BaseModel):
    """The contracts to judge, and the contract files the loader could not read."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contracts: tuple[ModelEffectContractDocument, ...] = ()
    unreadable: tuple[str, ...] = Field(
        default=(),
        description="Paths the loader could not parse; carried to the report",
    )
