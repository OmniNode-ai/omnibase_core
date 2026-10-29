# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The test-write guard's decision: refused with the runner signal, or admitted (OMN-19513)."""

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelLedgerWriteGuardDecision"]


class ModelLedgerWriteGuardDecision(BaseModel):
    """The test-write guard's decision: refused with the runner signal, or admitted (OMN-19513)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    refused: bool
    signal: str | None = None
