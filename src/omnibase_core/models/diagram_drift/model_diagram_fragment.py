# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A contract fragment the core models accepted, for the diagram-drift check (OMN-21510)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ModelDiagramFragment(BaseModel):
    """A fragment kept as the raw mapping the file holds.

    The graph model keeps only ``node_id``, ``node_type`` and ``depends_on`` of a node and drops
    ``description`` and ``step_config``; the drawing uses the descriptions, so it reads the raw
    mapping beside the structural validation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(description="state_machine or graph")
    initial_state: str = Field(
        default="", description="Initial state of a state machine"
    )
    terminal_states: tuple[str, ...] = Field(
        default=(), description="Terminal states of a state machine"
    )
    transitions: tuple[dict[str, JsonValue], ...] = Field(
        default=(), description="Transitions of a state machine, in contract order"
    )
    nodes: tuple[dict[str, JsonValue], ...] = Field(
        default=(), description="Nodes of a graph, in contract order"
    )
