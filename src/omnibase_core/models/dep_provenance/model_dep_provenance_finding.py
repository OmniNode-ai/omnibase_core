# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A finding row of the dependency provenance contract: its message and its remedy."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelDepProvenanceFinding"]


class ModelDepProvenanceFinding(BaseModel):
    """Presentation lives in the contract rule row; the checker only fills the fields."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
    message: str
    remediation: str
