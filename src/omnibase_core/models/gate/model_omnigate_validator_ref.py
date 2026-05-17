# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OmniGate validator reference model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelOmniGateValidatorRef(BaseModel):
    """Reference to a configured OmniGate validator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    config: dict[str, int | str | bool] | None = None


__all__ = ["ModelOmniGateValidatorRef"]
