# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed YAML document for temporary extra-forbid waivers."""

from pydantic import BaseModel, ConfigDict, Field


class ModelViolationWaiversDocument(BaseModel):
    """Container for governed, expiring model-validation waivers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    waivers: tuple[dict[str, object], ...] = Field(default_factory=tuple)


__all__ = ["ModelViolationWaiversDocument"]
