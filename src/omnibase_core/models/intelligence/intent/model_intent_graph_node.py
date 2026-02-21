# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Intent graph node (vertex) model.

Represents a vertex in the Intent Graph — a directed graph where nodes are
distinct intent classes and edges are observed session transitions between
those classes. Graph nodes aggregate occurrence statistics across all observed
sessions.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass

__all__ = ["ModelIntentGraphNode"]


class ModelIntentGraphNode(BaseModel):
    """Intent graph vertex.

    Aggregates statistics for a single intent class as observed across all
    user sessions. Part of the intent graph that enables transition analysis
    and pattern discovery.

    Attributes:
        node_id: Unique identifier for this graph node.
        intent_class: The intent class this node represents.
        session_id: Reference session used when this node was first created
            or last updated (e.g., for provenance tracing).
        occurrence_count: Total number of times this intent class was observed
            across all tracked sessions.
        avg_cost_usd: Average cost in US dollars for sessions classified under
            this intent class.
        success_rate: Fraction of sessions with this intent class that
            completed successfully, in [0.0, 1.0].

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.intelligence.enum_intent_class import EnumIntentClass
        >>> node = ModelIntentGraphNode(
        ...     node_id=uuid4(),
        ...     intent_class=EnumIntentClass.REFACTOR,
        ...     session_id="session-xyz",
        ...     occurrence_count=142,
        ...     avg_cost_usd=0.018,
        ...     success_rate=0.94,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    node_id: UUID = Field(
        description="Unique identifier for this graph node",
    )
    intent_class: EnumIntentClass = Field(
        description="The intent class this node represents",
    )
    # string-id-ok: External session ID (Claude Code, CLI, etc.), not ONEX-internal UUID
    session_id: str = Field(
        description=(
            "Reference session used when this node was first created or last updated "
            "(for provenance tracing)"
        ),
    )
    occurrence_count: int = Field(
        ge=0,
        description="Total number of times this intent class was observed across all tracked sessions",
    )
    avg_cost_usd: float = Field(
        ge=0.0,
        description="Average cost in US dollars for sessions classified under this intent class",
    )
    success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of sessions with this intent class that completed successfully, in [0.0, 1.0]"
        ),
    )
