"""Activation patterns model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelActivationPatterns(BaseModel):
    """Agent activation and routing patterns.

    Defines how and when the agent should be activated based on
    triggers, context, and capability matching.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    explicit_triggers: list[str] | None = None
    context_triggers: list[str] | None = None
    capability_matching: list[str] | None = None
    activation_keywords: list[str] | None = None
    aliases: list[str] | None = None


__all__ = ["ModelActivationPatterns"]
