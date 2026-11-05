# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Ledger failure row an error chain scenario expects (OMN-22478)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelChainScenarioLedgerRow(BaseModel):
    """The ledger failure row and the subject it is written for."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    row_type: str = Field(
        ..., min_length=1, description="Ledger row type of the failure row."
    )
    subject: str = Field(
        ..., min_length=1, description="Subject the row and the reading name."
    )


__all__ = ["ModelChainScenarioLedgerRow"]
