"""ONEX integration model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelOnexIntegration(BaseModel):
    """ONEX framework integration settings.

    Configures how the agent integrates with ONEX infrastructure including
    typing, error handling, naming conventions, and architecture patterns.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    strong_typing: str | None = None
    error_handling: str | None = None
    naming_conventions: str | None = None
    contract_driven: str | None = None
    registry_pattern: str | None = None
    four_node_architecture: dict[str, str] | None = None


__all__ = ["ModelOnexIntegration"]
