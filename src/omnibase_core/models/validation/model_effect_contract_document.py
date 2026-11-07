# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelEffectContractDocument (OMN-22911)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEffectContractDocument(BaseModel):
    """One parsed node contract and the label (its path) used in findings."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str = Field(description="Label of the contract, normally its file path")
    document: dict[str, object] = Field(description="The parsed contract mapping")
