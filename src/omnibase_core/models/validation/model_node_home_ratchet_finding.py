# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""A finding from the node-home ratchet (OMN-20702)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ModelNodeHomeRatchetFinding(BaseModel):
    """A forbidden node or a baseline entry that must be removed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: Literal[
        "node-outside-market",
        "baseline-stale",
        "baseline-growth",
        "baseline-removed",
        "entry-point-outside-market",
    ]
    path: str
    message: str

    def format(self) -> str:
        """Render the CLI's one-line finding."""
        return f"{self.code} {self.path}: {self.message}"


__all__ = ["ModelNodeHomeRatchetFinding"]
