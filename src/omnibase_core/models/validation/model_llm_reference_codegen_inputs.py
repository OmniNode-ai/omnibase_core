# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed input projection for generated LLM model and endpoint references."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelLlmReferenceCodegenInputs(BaseModel):
    """Registry root fields consumed by the LLM reference code generator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoints: tuple[dict[str, object], ...] = Field(default_factory=tuple)
    models: dict[str, object] = Field(default_factory=dict)
    schema_version: str | None = None
    model_registry_version: ModelSemVer | None = None
    # The owning registry uses this exact key for a dated pricing snapshot ID,
    # not a semantic-version value.
    pricing_manifest_version: str | None = None
    observed_at: str | None = None

    @field_validator("model_registry_version", mode="before")
    @classmethod
    def parse_model_registry_version(cls, value: object) -> object:
        """Normalize the registry's serialized semantic version at the boundary."""
        if isinstance(value, str):
            return ModelSemVer.parse(value)
        return value


__all__ = ["ModelLlmReferenceCodegenInputs"]
