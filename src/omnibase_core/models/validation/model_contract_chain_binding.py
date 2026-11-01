# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed contract-chain binding."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelContractChainBinding(BaseModel):
    """A literal chain marker or a committed generated case."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    obligation_ref: str
    file: str
    line: int = Field(ge=1)
    overlays: tuple[str, ...] = ()
