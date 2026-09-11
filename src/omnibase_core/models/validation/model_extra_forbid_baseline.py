# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed frozen baseline for the Pydantic extra-forbid ratchet."""

from pydantic import BaseModel, ConfigDict, Field


class ModelExtraForbidBaseline(BaseModel):
    """Fail-closed schema for extra-forbid violation fingerprints."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    violations: list[str] = Field(default_factory=list)


__all__ = ["ModelExtraForbidBaseline"]
