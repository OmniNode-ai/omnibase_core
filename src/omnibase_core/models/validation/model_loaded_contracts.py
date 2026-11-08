# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelLoadedContracts (OMN-22911)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_effect_contract_document import (
    ModelEffectContractDocument,
)


class ModelLoadedContracts(BaseModel):
    """What one directory scan read, and what it could not read."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    documents: tuple[ModelEffectContractDocument, ...] = ()
    unreadable: tuple[str, ...] = ()
    root_unavailable: str = Field(
        default="",
        description="Why the scan root could not be read; empty when the root was scanned",
    )
