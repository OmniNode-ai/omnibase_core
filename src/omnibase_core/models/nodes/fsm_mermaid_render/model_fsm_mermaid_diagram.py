# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A validated FSM subcontract drawn as a Mermaid state diagram (OMN-21589).

The diagram is derived from the contract block, never drawn by hand, so a reviewer
regenerates it from the ``state_transitions`` text it documents.
"""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.contracts.subcontracts.model_fsm_subcontract import (
    ModelFSMSubcontract,
)


class ModelFsmMermaidDiagram(BaseModel):
    """The ``stateDiagram-v2`` text of one machine."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str

    @classmethod
    def from_machine(cls, machine: ModelFSMSubcontract) -> "ModelFsmMermaidDiagram":
        """Draw the initial edge, one edge per transition in declared order, one per terminal state."""
        lines = ["stateDiagram-v2", f"    [*] --> {machine.initial_state}"]
        lines.extend(
            f"    {t.from_state} --> {t.to_state}: {t.trigger}"
            for t in machine.transitions
        )
        lines.extend(f"    {state} --> [*]" for state in machine.terminal_states)
        return cls(text="\n".join(lines) + "\n")
