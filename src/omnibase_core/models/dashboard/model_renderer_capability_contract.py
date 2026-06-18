# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RendererCapabilityContract — what a renderer can render.

Phase 0 UI contract primitive (OMN-13130, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §6, §7).

A renderer advertises the component kinds it supports, its interaction model,
accessibility tier, contract version, and granular ``supports_*`` capability
flags. **Model only this phase** — the omnimarket reducer
(``node_renderer_capability_projection``), its command topic, and the
heartbeat-backed projection are Phase 1. No node, topic, or projection is
created here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_accessibility_tier import EnumAccessibilityTier
from omnibase_core.enums.enum_renderer_interaction_model import (
    EnumRendererInteractionModel,
)
from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelRendererCapabilityContract"]


class ModelRendererCapabilityContract(BaseModel):
    """A renderer's advertised capability surface.

    ``supported_component_kinds`` reuses the shipped ``EnumWidgetType``
    vocabulary so capability negotiation is anchored on the component kinds that
    already exist. The ``supports_*`` flags express granular interaction
    capabilities a contract may require. ``contract_version`` lets the capability
    projection track schema drift per renderer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    renderer_id: str = Field(  # string-id-ok: human-readable renderer label, not a UUID
        ...,
        description="Stable renderer identifier (e.g. 'ui.effect.web', 'ui.effect.cli')",
        min_length=1,
    )
    platform: str = Field(
        ...,
        description="Target platform the renderer runs on (e.g. 'web', 'ios', 'cli')",
        min_length=1,
    )
    supported_component_kinds: tuple[EnumWidgetType, ...] = Field(
        ...,
        description="Component kinds this renderer can render (shipped EnumWidgetType)",
    )
    interaction_model: EnumRendererInteractionModel = Field(
        ...,
        description="Interaction model the renderer advertises",
    )
    accessibility_tier: EnumAccessibilityTier = Field(
        ...,
        description="WCAG-aligned accessibility tier the renderer guarantees",
    )
    contract_version: ModelSemVer = Field(
        ...,
        description="Semantic version of the capability contract this row declares",
    )
    supports_interaction: bool = Field(
        default=False,
        description="Whether the renderer can emit user-driven command actions",
    )
    supports_streaming: bool = Field(
        default=False,
        description="Whether the renderer can consume streaming projection updates",
    )
    supports_theming: bool = Field(
        default=False,
        description="Whether the renderer honors a versioned theme contract",
    )
