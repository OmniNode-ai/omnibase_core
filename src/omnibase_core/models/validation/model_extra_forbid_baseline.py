# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Frozen FQN set used by the extra-forbid ratchet."""

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ModelExtraForbidBaseline(BaseModel):
    """Baseline document containing the exact historical model FQNs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    violations: tuple[StrictStr, ...] = Field(default_factory=tuple)


__all__ = ["ModelExtraForbidBaseline"]
