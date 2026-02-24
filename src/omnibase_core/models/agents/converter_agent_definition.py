# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Converter from ModelAgentDefinition to routing-view dictionary.

This module provides the ``to_routing_config`` function which extracts the
routing-relevant subset of a full agent definition for use by the agent
routing layer (e.g. UserPromptSubmit hook, omniintelligence routing service).

The routing view intentionally excludes heavyweight authoring fields (philosophy
details, workflow templates, quality gates, etc.) and focuses on the fields
needed to match an incoming prompt to an agent:

    - Agent name and type (identity)
    - Primary capabilities (capability matching)
    - Activation triggers (keyword / context matching)
    - RAG query settings (intelligence retrieval tuning)
    - Agent aliases (short-name look-up)

Example::

    >>> from omnibase_core.models.agents import ModelAgentDefinition
    >>> from omnibase_core.models.agents.converter_agent_definition import (
    ...     to_routing_config,
    ... )
    >>> import yaml
    >>> with open("agent.yaml") as f:
    ...     data = yaml.safe_load(f)
    >>> agent = ModelAgentDefinition.model_validate(data)
    >>> routing = to_routing_config(agent)
    >>> routing["name"]
    'agent-pr-review'
"""

from __future__ import annotations

from typing import Any

from omnibase_core.models.agents.model_agent_definition import ModelAgentDefinition


def to_routing_config(definition: ModelAgentDefinition) -> dict[str, Any]:
    """Convert a full agent definition to a compact routing-view dictionary.

    Extracts the fields relevant to agent routing and capability matching while
    discarding heavyweight authoring sections (philosophy, workflow templates,
    quality gates, success metrics, integration points, transformation context).

    Args:
        definition: A validated ``ModelAgentDefinition`` instance.

    Returns:
        A dictionary containing the routing-relevant fields:

        - ``name`` (str): Unique agent name from identity.
        - ``agent_type`` (str): Agent type classifier.
        - ``description`` (str): Agent purpose description.
        - ``title`` (str | None): Display title.
        - ``domain`` (str | None): Domain specialization.
        - ``aliases`` (list[str]): Name aliases for fuzzy routing.
        - ``activation_keywords`` (list[str]): Routing trigger keywords.
        - ``explicit_triggers`` (list[str]): Exact trigger phrases.
        - ``context_triggers`` (list[str]): Context-based trigger phrases.
        - ``primary_capabilities`` (list[str]): Primary capabilities list.
        - ``match_count`` (int | None): RAG result count override.
        - ``confidence_threshold`` (float | None): RAG confidence override.
        - ``skills`` (list[str]): Referenced Claude skills.

    Example::

        >>> routing = to_routing_config(agent_definition)
        >>> assert "name" in routing
        >>> assert isinstance(routing["primary_capabilities"], list)

    """
    identity = definition.agent_identity
    activation = definition.activation_patterns
    framework = definition.framework_integration

    # Resolve RAG settings from framework.rag_queries (primary source)
    match_count: int | None = None
    confidence_threshold: float | None = None
    if framework is not None and framework.rag_queries is not None:
        match_count = framework.rag_queries.match_count
        confidence_threshold = framework.rag_queries.confidence_threshold

    return {
        # Identity
        "name": identity.name,
        "agent_type": definition.agent_type,
        "description": identity.description,
        "title": identity.title,
        "domain": identity.domain,
        "aliases": (list(identity.aliases) if identity.aliases is not None else []),
        # Activation / routing triggers
        "activation_keywords": (
            list(activation.activation_keywords)
            if activation is not None and activation.activation_keywords is not None
            else []
        ),
        "explicit_triggers": (
            list(activation.explicit_triggers)
            if activation is not None and activation.explicit_triggers is not None
            else []
        ),
        "context_triggers": (
            list(activation.context_triggers)
            if activation is not None and activation.context_triggers is not None
            else []
        ),
        # Capabilities
        "primary_capabilities": list(definition.capabilities.primary),
        # RAG retrieval settings
        "match_count": match_count,
        "confidence_threshold": confidence_threshold,
        # Skills references
        "skills": (
            list(definition.claude_skills_references)
            if definition.claude_skills_references is not None
            else []
        ),
    }


__all__ = ["to_routing_config"]
