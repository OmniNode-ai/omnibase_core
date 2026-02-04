"""Transformation context model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelTransformationContext(BaseModel):
    """Transformation context for polymorphic agents.

    Defines how the agent can transform its identity and capabilities
    based on context. Supports agent identity assumption and
    capability inheritance patterns.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    identity_assumption_triggers: list[str] | None = None
    capability_inheritance: list[str] | None = None
    execution_context: list[str] | None = None
    migration_from: str | None = None
    migration_to: str | None = None


__all__ = ["ModelTransformationContext"]
