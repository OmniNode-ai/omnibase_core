"""
Typed model for node graph information.

Provides a strongly-typed model for node information passed in
node graph ready events, replacing dict[str, Any] patterns.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelNodeGraphInfo"]


class ModelNodeGraphInfo(BaseModel):
    """
    Typed node information for graph wiring events.

    Replaces dict[str, Any] in node graph events with explicit
    typed fields for node identification and subscription wiring.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        from_attributes=True,
    )

    node_id: UUID = Field(
        description="Unique identifier of the node",
    )
    node_name: str = Field(
        description="Human-readable name of the node",
    )
    node_type: str = Field(
        description="Type of node (EFFECT, COMPUTE, REDUCER, ORCHESTRATOR)",
    )
    declared_subscriptions: list[str] = Field(
        default_factory=list,
        description="Topics this node declares subscriptions to",
    )
    contract_path: str | None = Field(
        default=None,
        description="Path to the node's contract YAML file",
    )
