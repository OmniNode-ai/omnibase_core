# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Residue ratchet entry model for the routing-authority check node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelResidueEntry(BaseModel):
    """One residue file with a baselined violation count."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    file_rel: str
    baseline_count: int
    debt_ticket: str
    description: str
