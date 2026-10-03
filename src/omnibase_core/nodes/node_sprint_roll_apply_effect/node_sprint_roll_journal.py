# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The sprint roll's write-ahead journal (OMN-20397)."""

from __future__ import annotations

from pathlib import Path

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect.runtime_sprint_roll_apply import (
    MUTATION,
    GraphQLTransport,
    write_payload,
)

__all__ = ["NodeSprintRollJournal"]


class NodeSprintRollJournal:
    """Appends each write to a manifest BEFORE the transport is asked to send it.

    The ordering is the guarantee. A crash between the journal line and the mutation
    leaves a manifest entry for a write that never happened, and undoing that is a no-op;
    the reverse ordering would leave a write with no record, which nothing can undo.
    """

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.writes: list[ModelSprintRollWrite] = []

    def record(self, write: ModelSprintRollWrite) -> None:
        self.writes.append(write)
        if self.path is None:
            return
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(write.model_dump_json() + "\n")
            handle.flush()

    def send(self, transport: GraphQLTransport, write: ModelSprintRollWrite) -> None:
        """Journal, then mutate. Never the other way round."""
        self.record(write)
        transport(MUTATION, {"id": write.issue_uuid, "in": write_payload(write)})
