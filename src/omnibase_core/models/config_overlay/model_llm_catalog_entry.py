# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One logical model in the ``llm.catalog`` overlay (OMN-19391)."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_llm_tier_class import EnumLlmTierClass


class ModelLlmCatalogEntry(BaseModel):
    """Served names, provider, window, capabilities and tier class of one model.

    ``tier_class`` and ``free`` are both required: a model's class and whether
    it costs anything are stated by the catalog, never inferred from its name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    served_model_names: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="Names the serving backends accept for this model.",
    )
    provider: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Wire protocol family of the serving backends.",
    )
    context_window_tokens: int = Field(
        ..., gt=0, description="Maximum context length in tokens."
    )
    capability_tags: tuple[str, ...] = Field(
        default=(), description="Capabilities the model is catalogued for."
    )
    tier_class: EnumLlmTierClass = Field(
        ..., description="Cost-and-locality class of the model."
    )
    free: bool = Field(..., description="True when a call costs nothing per token.")

    @model_validator(mode="after")
    def _names_are_non_blank(self) -> Self:
        blank = [
            n
            for n in (*self.served_model_names, *self.capability_tags)
            if not n.strip()
        ]
        if blank:
            raise ValueError("served_model_names and capability_tags must not be blank")
        return self


__all__ = ["ModelLlmCatalogEntry"]
