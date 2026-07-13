# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Model for capabilities discovered via runtime reflection."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import JsonType


class ModelDiscoveredCapabilities(BaseModel):
    """Capabilities discovered via runtime reflection.

    This model represents what introspection discovers about a node at runtime,
    as opposed to ModelNodeCapabilities which represents declared/contract capabilities.

    Attributes:
        operations: Method names matching operation keywords (execute, handle, process).
        has_fsm: Whether the node has FSM state management.
        method_signatures: Mapping of method names to their signature strings.
        attributes: Additional discovered attributes (flexible JSON storage).

    Example:
        >>> caps = ModelDiscoveredCapabilities(
        ...     operations=("execute", "query", "batch_execute"),
        ...     has_fsm=True,
        ...     method_signatures={"execute": "(query: str) -> list[dict]"},
        ... )
    """

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    operations: tuple[str, ...] = Field(
        default=(),
        description="Method names matching operation keywords (execute, handle, process)",
    )
    has_fsm: bool = Field(
        default=False,
        description="Whether the node has FSM state management",
    )
    method_signatures: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of method names to their signature strings",
    )
    attributes: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Additional discovered attributes",
    )


__all__ = ["ModelDiscoveredCapabilities"]
