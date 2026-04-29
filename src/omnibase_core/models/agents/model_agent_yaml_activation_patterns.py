# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Strict activation patterns model for agent YAML config files."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelActivationPatterns(BaseModel):
    """Activation trigger patterns for an agent config YAML.

    Stricter variant: explicit_triggers is required and non-empty (enforced by validator).
    """

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    explicit_triggers: list[str] = Field(
        ..., description="Phrases that explicitly invoke this agent"
    )
    context_triggers: list[str] = Field(
        default_factory=list, description="Context-based activation phrases"
    )

    @field_validator("explicit_triggers")
    @classmethod
    def explicit_triggers_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            msg = "explicit_triggers must contain at least one trigger"
            raise ValueError(msg)
        return v


__all__ = ["ModelActivationPatterns"]
