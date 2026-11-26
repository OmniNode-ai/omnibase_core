# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""What one command of the consumer install check did (OMN-26670)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelCommandOutcome(BaseModel):
    """Exit code and combined output of one command, and whether its timeout ended it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    returncode: int
    output: str
    timed_out: bool = False
