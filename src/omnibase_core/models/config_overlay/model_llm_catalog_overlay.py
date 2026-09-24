# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ``llm.catalog`` overlay document body (OMN-19391)."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.config_overlay.model_llm_catalog_entry import (
    ModelLlmCatalogEntry,
)


class ModelLlmCatalogOverlay(BaseModel):
    """Logical model key to catalog entry. Holds no default model."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: Literal["llm_catalog.v1"] = Field(
        ..., description="Schema version tag."
    )
    models: dict[str, ModelLlmCatalogEntry] = Field(
        ...,
        min_length=1,
        description="Logical model key to its catalog entry.",
    )

    @model_validator(mode="after")
    def _keys_are_non_blank(self) -> Self:
        if any(not key.strip() for key in self.models):
            raise ValueError("llm.catalog model keys must not be blank")
        return self


__all__ = ["ModelLlmCatalogOverlay"]
