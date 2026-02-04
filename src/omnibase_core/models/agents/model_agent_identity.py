"""Agent identity model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelAgentIdentity(BaseModel):
    """Agent identity and metadata.

    Contains core identification fields for an agent including its unique name,
    description, and optional display/categorization attributes.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    name: str = Field(..., description="Unique agent identifier")
    description: str = Field(..., description="Agent purpose")
    title: str | None = None
    color: str | None = None
    task_agent_type: str | None = None
    specialization_level: str | None = None
    version: str | None = None
    domain: str | None = None
    short_name: str | None = None
    aliases: list[str] | None = None


__all__ = ["ModelAgentIdentity"]
