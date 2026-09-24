# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The five config-store overlay keys (OMN-19391).

Plan task B2 of knowledge-base-internal
``beta/plans/2026-09-23-remove-hardcoded-model-config.md`` section 3.1. Every
lab and house model value lives in one overlay document per key per scope; a
repository holds only the typed schema that validates it. Each key names the
repository and schema that owns it through :attr:`EnumConfigOverlayKey.schema_ref`.
"""

from __future__ import annotations

from enum import StrEnum, unique


@unique
class EnumConfigOverlayKey(StrEnum):
    """A config-store overlay key. The value is the key as the store spells it."""

    DELEGATION_LANE_OVERLAY = "delegation.lane_overlay"
    ROUTING_TIERS = "routing.tiers"
    LLM_CATALOG = "llm.catalog"
    LLM_PRICING = "llm.pricing"
    EMBEDDING_ENDPOINT = "embedding.endpoint"

    @property
    def schema_ref(self) -> str:
        """``<owning repository>:<schema name>`` of the schema this key's documents obey."""
        return _SCHEMA_REFS[self]


# The owning repository of each schema. delegation.lane_overlay and
# routing.tiers are owned above core (rule 7 layering), so core names them and
# never imports them.
_SCHEMA_REFS: dict[EnumConfigOverlayKey, str] = {
    EnumConfigOverlayKey.DELEGATION_LANE_OVERLAY: "omnibase_infra:bifrost_lane_overlay",
    EnumConfigOverlayKey.ROUTING_TIERS: "omnimarket:routing_tiers",
    EnumConfigOverlayKey.LLM_CATALOG: "omnibase_core:llm_catalog",
    EnumConfigOverlayKey.LLM_PRICING: "omnibase_core:llm_pricing",
    EnumConfigOverlayKey.EMBEDDING_ENDPOINT: "omnibase_core:embedding_endpoint",
}


__all__ = ["EnumConfigOverlayKey"]
