"""TypedDict for agent routing alternative entries.

Defines the TypedDictRoutingAlternative TypedDict for alternative agents
considered during routing decisions with their confidence scores.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictRoutingAlternative(TypedDict):
    """Typed structure for agent routing alternatives.

    Represents an alternative agent that was considered during routing
    with its associated confidence score.

    Attributes:
        agent_name: The name of the alternative agent.
        confidence: Confidence score for this agent (0.0 to 1.0).
    """

    agent_name: str
    confidence: float


__all__ = ["TypedDictRoutingAlternative"]
