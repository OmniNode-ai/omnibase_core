"""Quality gates model for YAML schema validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelQualityGates(BaseModel):
    """Quality gate requirements.

    Defines quality requirements and standards that must be met
    before agent work is considered complete.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    must_have_requirements: list[str] | None = None
    quality_standards: list[str] | None = None


__all__ = ["ModelQualityGates"]
