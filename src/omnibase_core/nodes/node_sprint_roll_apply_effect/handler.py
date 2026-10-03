# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeSprintRollApplyEffect — applies a sprint roll plan to Linear.

Architecture: EFFECT node. It writes, and it is the only half of the roll that does; the
placement arithmetic is the paired COMPUTE node's (OMN-20396) and arrives here already
decided, on :class:`ModelSprintRollApplyRequest`.

Two properties this handler exists to guarantee:

* A dry run sends nothing. It is the default, and it is provable from the transport
  rather than from anything this class reports about itself.
* Every mutation is journalled before it is sent, so a run interrupted halfway still
  leaves a manifest that reverses what it managed to do. The operator's rule for this
  roll is best guess now, audit after the sprint starts, and an audit with no undo is
  just a record of damage.

Ticket: OMN-20397 (parent OMN-20395).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_apply_request import (
    ModelSprintRollApplyRequest,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_apply_result import (
    ModelSprintRollApplyResult,
)
from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
)
from omnibase_core.nodes.node_sprint_roll_apply_effect.runtime_sprint_roll_apply import (
    GraphQLPayload,
    GraphQLTransport,
    SprintRollJournal,
    node_rows,
)

if TYPE_CHECKING:
    from pydantic import JsonValue

__all__ = ["NodeSprintRollApplyEffect"]

#: Linear's issue read, for the facts a placement plan does not carry: the issue's own
#: uuid (the plan speaks in identifiers), and what its project and state hold now, which
#: is what an undo restores.
ISSUE_QUERY = (
    'query($ids:[String!]!){issues(filter:{team:{key:{eq:"OMN"}},'
    "identifier:{in:$ids}},first:250){nodes{id identifier "
    "project{id} state{id} labels{nodes{id}}}}}"
)


class NodeSprintRollApplyEffect:
    """EFFECT handler that turns a roll plan into Linear mutations."""

    def __init__(self, transport: GraphQLTransport) -> None:
        self._transport = transport
        self._reads = 0
        self._writes = 0

    def _read(self, query: str, variables: GraphQLPayload) -> GraphQLPayload:
        self._reads += 1
        return self._transport(query, variables)

    def handle(
        self, request: ModelSprintRollApplyRequest
    ) -> ModelSprintRollApplyResult:
        """Definition-B canonical entry-point."""
        plan = request.plan
        wanted = [t for p in plan.placements for t in p.moved_in]
        wanted += list(plan.backlog_ticket_ids)
        if not wanted:
            return ModelSprintRollApplyResult(
                dry_run=request.dry_run, read_calls=0, write_calls=0
            )

        ids: list[JsonValue] = [str(i) for i in sorted(set(wanted))]
        current = self._read(ISSUE_QUERY, {"ids": ids})
        by_identifier = {
            str(node.get("identifier")): node for node in node_rows(current, "issues")
        }

        planned: list[ModelSprintRollWrite] = []
        for placement in plan.placements:
            for identifier in placement.moved_in:
                node = by_identifier.get(identifier)
                if node is None:
                    continue
                project = node.get("project")
                before = project.get("id") if isinstance(project, dict) else None
                after = str(placement.sprint_id)
                if before == after:
                    continue
                planned.append(
                    ModelSprintRollWrite(
                        issue_uuid=str(node.get("id")),
                        identifier=identifier,
                        field="projectId",
                        before=(str(before),) if before else None,
                        after=(after,),
                    )
                )

        if request.dry_run:
            # Nothing is sent and nothing is journalled: a dry run that wrote a manifest
            # would leave an undo record for writes that never happened.
            return ModelSprintRollApplyResult(
                dry_run=True,
                writes=tuple(planned),
                manifest_path=None,
                read_calls=self._reads,
                write_calls=0,
            )

        journal = SprintRollJournal(request.manifest_path)
        for write in planned:
            journal.send(self._transport, write)
            self._writes += 1
        return ModelSprintRollApplyResult(
            dry_run=False,
            writes=tuple(journal.writes),
            manifest_path=request.manifest_path,
            read_calls=self._reads,
            write_calls=self._writes,
        )
