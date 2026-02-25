# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""TypedDict for agent routing configuration.

This TypedDict defines the structure returned by
``converter_agent_definition.to_routing_config()``, providing typed access
to the routing-relevant subset of a full agent definition.

Related:
    - OMN-407: Agent definition YAML schema
    - converter_agent_definition.to_routing_config(): Returns this type

.. versionadded:: 0.6.0
"""

from __future__ import annotations

__all__ = ["TypedDictAgentRoutingConfig"]

from typing import TypedDict


class TypedDictAgentRoutingConfig(TypedDict):
    """TypedDict for the compact routing-view returned by to_routing_config().

    Attributes:
        name: Unique agent name from identity.
        agent_type: Agent type classifier string.
        description: Human-readable agent purpose description.
        title: Optional display title.
        domain: Optional domain specialization.
        aliases: Name aliases for fuzzy routing.
        activation_keywords: Routing trigger keywords.
        explicit_triggers: Exact trigger phrases.
        context_triggers: Context-based trigger phrases.
        primary_capabilities: Primary capabilities list.
        match_count: Optional RAG result count override.
        confidence_threshold: Optional RAG confidence override.
        skills: Referenced Claude skill names.
    """

    name: str
    agent_type: str
    description: str
    title: str | None
    domain: str | None
    aliases: list[str]
    activation_keywords: list[str]
    explicit_triggers: list[str]
    context_triggers: list[str]
    primary_capabilities: list[str]
    match_count: int | None
    confidence_threshold: float | None
    skills: list[str]
